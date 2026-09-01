@echo off
setlocal
cd /d %~dp0
where py >nul 2>nul
if %errorlevel%==0 (
  set PYTHON=py
) else (
  set PYTHON=python
)
if not exist .venv (
  %PYTHON% -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
set APP_ENV=development
set APP_SECRET=TSCO-local-review-2026-change-before-shared-use
set DATABASE_URL=sqlite:///./app/data/tsco_platform.db
set SEED_DEMO_DATA=true
set SHOW_DEMO_ACCOUNTS=false
set BOOTSTRAP_ADMIN_EMAIL=admin@tsco.local
set BOOTSTRAP_ADMIN_NAME=System Administrator
set BOOTSTRAP_ADMIN_PASSWORD=Demo123!
set REQUIRE_BOOTSTRAP_PASSWORD_CHANGE=false
set LMS_MODE=mock
set ENABLE_API_DOCS=true
start "" http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
endlocal
