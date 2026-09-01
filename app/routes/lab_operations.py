from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import templates
from ..models import Role, Site
from ..security import require_user
from ..services.lab_operations import blank_operations_db, get_operations_state, reconcile_operations_to_platform, save_operations_state

router = APIRouter(tags=["integrated laboratory operations"])
ALLOWED = {
    Role.LAB_TECHNICIAN.value, Role.SENIOR_CHEMIST.value, Role.QUALITY.value,
    Role.TECHNICAL_MANAGER.value, Role.MANAGEMENT.value, Role.SYSTEM_ADMIN.value,
}
BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_FILE = BASE_DIR / "lab_ops" / "index_template.html"

SECTION_INFO = {
    "dashboard": ("Operations Overview", "Management-level laboratory flow, workload and operational status."),
    "labprogress": ("Laboratory Progress", "Live team board showing sample priority, assignment and completion progress."),
    "supervisor": ("Technical Supervision", "Senior Chemist result search, review, retest, release and technical actions."),
    "batch": ("Samples & Batches", "Create, review and maintain laboratory batches and sample metadata."),
    "workstations": ("Test Workstations", "Enter results with quick procedures, method references and calculation support."),
    "finalreport": ("Reports", "Review and release controlled worksheet result forms and revisions."),
    "retained": ("Retained Samples", "Storage location, retention period, due dates and controlled disposal."),
    "quality": ("Quality Control", "QC status, trends, exceptions and release controls."),
    "knowledge": ("Methods & Procedures", "Controlled methods, SOPs, EOPs and quick operating guidance."),
    "tracking": ("Operations Records", "Searchable sample history, result actions and operational records."),
    "general": ("Laboratory Settings", "Site, staff, document and controlled calculation configuration."),
}
ROLE_SECTIONS = {
    Role.LAB_TECHNICIAN.value: {"labprogress", "workstations", "retained", "quality", "knowledge"},
    Role.SENIOR_CHEMIST.value: {"dashboard", "labprogress", "supervisor", "batch", "workstations", "finalreport", "retained", "quality", "knowledge", "tracking"},
    Role.QUALITY.value: {"dashboard", "labprogress", "finalreport", "retained", "quality", "knowledge", "tracking"},
    Role.TECHNICAL_MANAGER.value: set(SECTION_INFO),
    Role.MANAGEMENT.value: {"dashboard", "labprogress", "finalreport", "tracking"},
    Role.SYSTEM_ADMIN.value: set(SECTION_INFO),
}


def _site_for_user(db: Session, user) -> Site:
    site = db.get(Site, user.site_id) if user.site_id else None
    if not site:
        site = db.query(Site).filter(Site.code == "DMM").first()
    return site


def _authorized_section(user, requested: str) -> str:
    allowed = ROLE_SECTIONS.get(user.role, {"labprogress"})
    if requested in allowed:
        return requested
    preferred = ["labprogress", "dashboard", "workstations", "knowledge"]
    return next((item for item in preferred if item in allowed), next(iter(allowed)))


@router.get("/lab/operations")
def operations_shell(request: Request, section: str = "labprogress", db: Session = Depends(get_db)):
    user = require_user(request, db, ALLOWED)
    section = _authorized_section(user, section)
    title, description = SECTION_INFO[section]
    allowed_sections = ROLE_SECTIONS.get(user.role, {section})
    visible_info = {k: {"title": SECTION_INFO[k][0], "description": SECTION_INFO[k][1]} for k in allowed_sections if k in SECTION_INFO}
    return templates.TemplateResponse(
        "lab_operations.html",
        {"request": request, "user": user, "section": section, "section_title": title, "section_description": description, "section_info": visible_info},
    )


@router.get("/lab/operations/app", response_class=HTMLResponse)
def operations_console(request: Request, section: str = "labprogress", embed: int = 1, db: Session = Depends(get_db)):
    user = require_user(request, db, ALLOWED)
    section = _authorized_section(user, section)
    html = TEMPLATE_FILE.read_text(encoding="utf-8")
    embed_css = """
    <style id="platformEmbedStyle">
      html,body{background:transparent!important}
      body.platform-embed{min-height:0!important;background:transparent!important;overflow:hidden!important}
      body.platform-embed>header,body.platform-embed>nav{display:none!important}
      body.platform-embed main{padding:0 2px 24px!important;margin:0!important;max-width:none!important}
      body.platform-embed .page{scroll-margin-top:0!important}
      body.platform-embed .page.on{animation:none!important}
      body.platform-embed .dashboard-hero{margin-top:0!important}
      body.platform-embed .card{box-shadow:0 2px 10px rgba(16,42,67,.055)!important}
      body.platform-embed .modal{position:fixed!important}
      @media(max-width:760px){body.platform-embed main{padding:0 0 18px!important}}
    </style>
    """ if embed else ""
    injection = (
        embed_css
        + f"<script>window.TSCO_PLATFORM_ROLE={json.dumps(user.role)};"
        + f"window.TSCO_PLATFORM_USER={json.dumps(user.full_name)};"
        + f"window.TSCO_PLATFORM_SITE={json.dumps(user.site.code if user.site else 'DMM')};"
        + f"window.TSCO_PLATFORM_SECTION={json.dumps(section)};"
        + f"window.TSCO_PLATFORM_EMBED={json.dumps(bool(embed))};</script>"
    )
    html = html.replace("</head>", injection + "</head>", 1)
    boot = """
    <script>
    (function(){
      const embedded=!!window.TSCO_PLATFORM_EMBED;
      if(embedded){document.body.classList.add('platform-embed');}
      function notifyHeight(){
        if(!embedded||window.parent===window)return;
        const h=Math.max(document.documentElement.scrollHeight,document.body.scrollHeight,620);
        window.parent.postMessage({type:'TSCO_LAB_HEIGHT',height:h},location.origin);
      }
      function notifySection(section){
        if(!embedded||window.parent===window||!section)return;
        window.parent.postMessage({type:'TSCO_LAB_SECTION_CHANGE',section:String(section)},location.origin);
      }
      function openRequested(){
        const section=window.TSCO_PLATFORM_SECTION;
        if(typeof goPage==='function'&&section){try{goPage(section)}catch(_){}}
        setTimeout(notifyHeight,80);
      }
      function wrapNavigation(){
        if(typeof goPage!=='function'||goPage.__platformWrapped)return;
        const original=goPage;
        const wrapped=function(section){
          const result=original.apply(this,arguments);
          notifySection(section);
          setTimeout(notifyHeight,50);
          setTimeout(notifyHeight,220);
          return result;
        };
        wrapped.__platformWrapped=true;
        window.goPage=wrapped;
      }
      function boot(){
        openRequested();
        wrapNavigation();
        if(window.ResizeObserver){new ResizeObserver(()=>requestAnimationFrame(notifyHeight)).observe(document.body);}
        window.addEventListener('resize',notifyHeight);
        window.addEventListener('load',notifyHeight);
        document.addEventListener('click',()=>setTimeout(notifyHeight,120),true);
        setTimeout(notifyHeight,350);
      }
      if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
      window.addEventListener('message',event=>{
        if(event.origin!==location.origin)return;
        if(event.data&&event.data.type==='TSCO_LAB_SECTION'&&typeof goPage==='function'){
          goPage(event.data.section);
          setTimeout(notifyHeight,80);
        }
      });
    })();
    </script>
    """
    html = html.replace("</body>", boot + "</body>", 1)
    return HTMLResponse(html)


@router.get("/lab-ops/documents/{filename}")
def protected_document(filename: str, request: Request, db: Session = Depends(get_db)):
    require_user(request, db, ALLOWED)
    safe_name = Path(filename).name
    path = BASE_DIR / "lab_ops" / "documents" / safe_name
    if not path.exists() or not path.is_file():
        return JSONResponse({"error": "Document not found"}, status_code=404)
    return FileResponse(path, filename=safe_name)


@router.get("/api/lab-operations/data")
def operations_load(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, ALLOWED)
    site = _site_for_user(db, user)
    state, payload = get_operations_state(db, site)
    db.commit()
    return {"db": payload, "savedAt": state.updated_at.isoformat() if state.updated_at else datetime.utcnow().isoformat(), "revision": state.revision}


@router.put("/api/lab-operations/data")
async def operations_save(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, ALLOWED)
    site = _site_for_user(db, user)
    body = await request.json()
    state, current = get_operations_state(db, site)
    if body.get("operation") == "reset-operational":
        if user.role != Role.SYSTEM_ADMIN.value or body.get("confirmation") != "DELETE DAMMAM DATA":
            return JSONResponse({"error": "Reset requires system administrator"}, status_code=403)
        payload = blank_operations_db(site)
    else:
        payload = body.get("db") or current
        if not isinstance(payload, dict) or not isinstance(payload.get("batches"), list):
            return JSONResponse({"error": "Invalid operations database"}, status_code=400)
    save_operations_state(db, state, payload, user)
    reconcile_operations_to_platform(db, payload, site.id, user)
    db.commit()
    return {"ok": True, "db": payload, "savedAt": state.updated_at.isoformat(), "revision": state.revision}
