from __future__ import annotations

import os
from pathlib import Path

# Every path is resolved from this package location, so all runtime paths are absolute.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_ENV_FILE = (PROJECT_ROOT / ".env").resolve()


def load_local_env(path: str | Path = LOCAL_ENV_FILE, override: bool = False) -> None:
    """Load a tiny KEY=VALUE .env file without adding python-dotenv as a dependency."""
    env_path = Path(path).expanduser().resolve()
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (override or key not in os.environ):
            os.environ[key] = value


# Load local secrets/tuning before constants below are materialized.
load_local_env()

DATA_DIR = (PROJECT_ROOT / "data").resolve()
DB_DIR = (PROJECT_ROOT / "db").resolve()
PENDING_DIR = (DB_DIR / "pending").resolve()
COMPLETE_DIR = (DB_DIR / "complete").resolve()
ERROR_DIR = (DB_DIR / "error").resolve()
OUTPUT_DIR = (PROJECT_ROOT / "output").resolve()
PAPERS_DIR = (PROJECT_ROOT / "papers").resolve()
PROMPTS_DIR = (PROJECT_ROOT / "prompts").resolve()
GENERATED_DIR = (PROJECT_ROOT / "generated").resolve()
HYPOTHESES_DIR = (GENERATED_DIR / "hypotheses").resolve()
TEMPLATES_DIR = (GENERATED_DIR / "templates").resolve()
CANDIDATES_DIR = (GENERATED_DIR / "candidates").resolve()
SESSION_CACHE = (DB_DIR / "session_cache.pkl").resolve()

OPERATORS_JSON = (DATA_DIR / "REGULAR_operators.json").resolve()
DATA_FIELDS_JSON = (DATA_DIR / "GLB_D1_TOPDIV3000_data_fields.json").resolve()

API_BASE = "https://api.worldquantbrain.com"
REQUEST_TIMEOUT_SECONDS = float(os.getenv("WQB_REQUEST_TIMEOUT", "30"))
SESSION_CACHE_HOURS = float(os.getenv("WQB_SESSION_CACHE_HOURS", "3.5"))
SIMULATION_LIMIT = int(os.getenv("WQB_SIMULATION_LIMIT", "3"))
MULTI_SIMULATION_SIZE = int(os.getenv("WQB_MULTI_SIMULATION_SIZE", "10"))


def ensure_runtime_directories() -> None:
    for path in (
        DATA_DIR,
        DB_DIR,
        PENDING_DIR,
        COMPLETE_DIR,
        ERROR_DIR,
        OUTPUT_DIR,
        PAPERS_DIR,
        PROMPTS_DIR,
        GENERATED_DIR,
        HYPOTHESES_DIR,
        TEMPLATES_DIR,
        CANDIDATES_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
