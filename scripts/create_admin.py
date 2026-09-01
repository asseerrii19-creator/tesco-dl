from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Role, Site, User
from app.security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or reset a TSCO system administrator")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--site", default="DMM")
    args = parser.parse_args()
    if len(args.password) < 10:
        raise SystemExit("Password must be at least 10 characters")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        site = db.scalar(select(Site).where(Site.code == args.site.upper()))
        if not site:
            site = Site(code=args.site.upper(), name=args.site.upper(), laboratory_name="Laboratory")
            db.add(site)
            db.flush()
        email = args.email.lower().strip()
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.full_name = args.name.strip()
            user.password_hash = hash_password(args.password)
            user.role = Role.SYSTEM_ADMIN.value
            user.site_id = site.id
            user.active = True
            user.must_change_password = True
            action = "updated"
        else:
            user = User(
                email=email,
                full_name=args.name.strip(),
                password_hash=hash_password(args.password),
                role=Role.SYSTEM_ADMIN.value,
                site_id=site.id,
                active=True,
                must_change_password=True,
            )
            db.add(user)
            action = "created"
        db.commit()
        print(f"Administrator {action}: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
