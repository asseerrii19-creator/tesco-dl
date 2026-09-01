# Deployment Quick Start

## UAT with Docker Compose

```bash
cp .env.uat.example .env
nano .env
docker compose config
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/api/v1/health
```

## Logs

```bash
docker compose logs -f web
docker compose logs -f db
```

## Database migration

```bash
docker compose exec web alembic current
docker compose exec web alembic upgrade head
```

## Initial administration

1. Open the Employee portal.
2. Sign in with `BOOTSTRAP_ADMIN_EMAIL` and the one-time password.
3. Change the password immediately.
4. Add companies.
5. Add users and assign roles/company scope/site.
6. Add quotations, POs and asset master records.
7. Keep `LMS_MODE=mock` during UAT.

## Production configuration

Use `.env.production.example` as a checklist, but store secrets in the corporate secret manager. Set:

- `APP_ENV=production`
- `SEED_DEMO_DATA=false`
- `SHOW_DEMO_ACCOUNTS=false`
- `ENABLE_PUBLIC_TRACKING=false` unless explicitly approved
- `ENABLE_API_DOCS=false`
- strong `APP_SECRET`, DB password and bootstrap credentials

## Backup scope

Back up all three:

- PostgreSQL database
- uploaded sample photos/files
- generated barcode/tag files

A database-only backup is not sufficient.
