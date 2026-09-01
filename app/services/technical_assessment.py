from __future__ import annotations

import json
import math
import re
from typing import Any

from sqlalchemy.orm import Session

from ..models import SampleRequest
from .lab_operations import get_operations_state


def _number(value: Any) -> float | None:
    if value is None:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value).replace(",", "."))
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def _latest_results(payload: dict[str, Any], sample_key: str) -> list[dict[str, Any]]:
    rows = [r for r in payload.get("results", []) if str(r.get("sample", "")).upper() == sample_key.upper()]
    rows.sort(key=lambda r: str(r.get("ts", "")))
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        latest[str(row.get("test", ""))] = row
    return list(latest.values())


def _find(rows: list[dict[str, Any]], *patterns: str) -> tuple[str, float] | None:
    for row in reversed(rows):
        name = str(row.get("test", ""))
        low = name.lower()
        if any(re.search(pattern, low) for pattern in patterns):
            value = _number(row.get("result"))
            if value is not None:
                return name, value
    return None


def _band(value: float, good_test, fair_test) -> str:
    if good_test(value):
        return "GOOD"
    if fair_test(value):
        return "FAIR"
    return "POOR"


def _iec_dga_fault(g: dict[str, float]) -> dict[str, Any] | None:
    required = ["H2", "CH4", "C2H6", "C2H4", "C2H2"]
    if not all(k in g and g[k] is not None for k in required):
        return None
    def ratio(a: str, b: str) -> float | None:
        if not g.get(b):
            return None
        return g[a] / g[b]
    r1 = ratio("C2H2", "C2H4")
    r2 = ratio("CH4", "H2")
    r3 = ratio("C2H4", "C2H6")
    if r2 is None or r3 is None:
        return None
    fault = "UNDETERMINED"
    if r2 < 0.1 and r3 < 0.2:
        fault = "PD"
    elif r1 is not None and r1 > 1 and 0.1 <= r2 <= 0.5 and r3 > 1:
        fault = "D1"
    elif r1 is not None and 0.6 <= r1 <= 2.5 and 0.1 <= r2 <= 1 and r3 > 2:
        fault = "D2"
    elif r2 > 1 and r3 < 1:
        fault = "T1"
    elif r1 is not None and r1 < 0.1 and r2 > 1 and 1 <= r3 <= 4:
        fault = "T2"
    elif r1 is not None and r1 < 0.2 and r2 > 1 and r3 > 4:
        fault = "T3"
    return {"fault": fault, "ratios": {"C2H2/C2H4": r1, "CH4/H2": r2, "C2H4/C2H6": r3}}


def assess_sample(db: Session, sample: SampleRequest) -> dict[str, Any]:
    state, payload = get_operations_state(db, sample.site)
    key = (sample.lms_number or sample.request_number).upper()
    rows = _latest_results(payload, key)
    findings: list[dict[str, Any]] = []

    bdv = _find(rows, r"breakdown voltage.*2\.5", r"bdv.*2\.5")
    if bdv:
        findings.append({"test": bdv[0], "value": bdv[1], "condition": _band(bdv[1], lambda v: v > 60, lambda v: 50 <= v <= 60), "reference": "IEC 60422:2024 Table 5 — screening profile A"})
    water = _find(rows, r"water content kf", r"water content(?!.*20)")
    if water:
        findings.append({"test": water[0], "value": water[1], "condition": _band(water[1], lambda v: v < 15, lambda v: 15 <= v <= 20), "reference": "IEC 60422:2024 Table 5 — screening profile A"})
    ddf = _find(rows, r"dissipation factor.*90")
    if ddf:
        findings.append({"test": ddf[0], "value": ddf[1], "condition": _band(ddf[1], lambda v: v < 0.10, lambda v: 0.10 <= v <= 0.20), "reference": "IEC 60422:2024 Table 5 — screening profile A"})
    resistivity = _find(rows, r"resistivity")
    if resistivity:
        findings.append({"test": resistivity[0], "value": resistivity[1], "condition": _band(resistivity[1], lambda v: v > 10, lambda v: 3 <= v <= 10), "reference": "IEC 60422:2024 Table 5 — screening profile A"})
    ift = _find(rows, r"interfacial tension", r"\bift\b")
    if ift:
        findings.append({"test": ift[0], "value": ift[1], "condition": _band(ift[1], lambda v: v > 28, lambda v: 22 <= v <= 28), "reference": "IEC 60422:2024 Table 5 — inhibited-oil screening"})

    gases: dict[str, float] = {}
    aliases = {
        "H2": [r"dga:h2", r"\bhydrogen\b"], "CH4": [r"dga:ch4", r"\bmethane\b"],
        "C2H6": [r"dga:c2h6", r"\bethane\b"], "C2H4": [r"dga:c2h4", r"\bethylene\b"],
        "C2H2": [r"dga:c2h2", r"\bacetylene\b"], "CO": [r"dga:co$", r"carbon monoxide"],
        "CO2": [r"dga:co2", r"carbon dioxide"], "O2": [r"dga:o2", r"\boxygen\b"], "N2": [r"dga:n2", r"\bnitrogen\b"],
    }
    for gas, pats in aliases.items():
        found = _find(rows, *pats)
        if found:
            gases[gas] = found[1]
    dga = _iec_dga_fault(gases)
    if dga and gases.get("CO"):
        dga["ratios"]["CO2/CO"] = gases.get("CO2", 0) / gases["CO"]

    severity = {"GOOD": 0, "FAIR": 1, "POOR": 2}
    overall = max((f["condition"] for f in findings), key=lambda x: severity[x], default="NOT ASSESSED")
    observations: list[str] = []
    actions: list[str] = []
    if any(f["condition"] == "POOR" for f in findings):
        observations.append("One or more oil-condition parameters are in the Poor screening band.")
        actions.append("Confirm abnormal results against history and consider a fresh sample before final action.")
    elif any(f["condition"] == "FAIR" for f in findings):
        observations.append("Oil deterioration is detectable in at least one screening parameter.")
        actions.append("Review complementary tests and consider increased sampling frequency.")
    elif findings:
        observations.append("Available screened parameters are within the Good band.")
        actions.append("Continue normal sampling, subject to trend and asset-specific requirements.")
    if water and bdv:
        observations.append("Water and BDV should be evaluated together rather than as isolated results.")
    if ift:
        actions.append("Review IFT together with acidity and DDF when ageing or contamination is suspected.")
    if dga:
        observations.append(f"IEC 60599 gas-ratio screening result: {dga['fault']}.")
        actions.append("Use gas history, rates of increase, equipment context and Senior Chemist judgement before diagnosis or recommendation.")

    return {
        "sample_key": key, "profile": "IEC 60422:2024 + IEC 60599:2022 screening",
        "results_count": len(rows), "overall": overall, "findings": findings,
        "gases": gases, "dga": dga, "observations": observations, "suggested_actions": actions,
        "disclaimer": "System-assisted internal screening only. Senior Chemist approval is required; client/manufacturer limits take precedence where applicable.",
    }
