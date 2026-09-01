from pathlib import Path

path = Path(__file__).resolve().parents[1] / "app" / "data" / "tsco_platform.db"
if path.exists():
    path.unlink()
    print(f"Removed {path}")
else:
    print("Demo database is already clean")
