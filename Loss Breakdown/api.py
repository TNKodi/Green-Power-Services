import os
import runpy
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    import uvicorn
except Exception as exc:
    uvicorn = None
    UVICORN_IMPORT_ERROR = exc
else:
    UVICORN_IMPORT_ERROR = None

SCRIPT_PATH = Path(__file__).with_name("Loss Breakdown.py")
MODULE_GLOBALS = runpy.run_path(str(SCRIPT_PATH))
RUN_LOSS_BREAKDOWN = MODULE_GLOBALS.get("run_loss_breakdown")
LOAD_ENV_FILE = MODULE_GLOBALS.get("load_env_file")
ENV_PATH = Path(__file__).with_name(".env")


class RunRequest(BaseModel):
    main_asset_id: Optional[str] = None
    max_depth: int = 3
    process_depth: int = 3
    env_overrides: Dict[str, str] = Field(default_factory=dict)


def _ensure_env_loaded() -> None:
    if callable(LOAD_ENV_FILE) and ENV_PATH.exists():
        LOAD_ENV_FILE(str(ENV_PATH))


def _run_service(request: RunRequest) -> Dict[str, Any]:
    if not callable(RUN_LOSS_BREAKDOWN):
        raise RuntimeError("run_loss_breakdown function is not available in 'Loss Breakdown.py'.")

    print("[API] Step 1/4: Loading environment from .env if available")
    _ensure_env_loaded()

    env_overrides = dict(request.env_overrides)
    if request.main_asset_id:
        env_overrides["THINGBOARD_ASSET_ID"] = request.main_asset_id

    print("[API] Step 2/4: Preparing execution parameters")
    print(
        f"[API] main_asset_id={env_overrides.get('THINGBOARD_ASSET_ID')} "
        f"max_depth={request.max_depth} process_depth={request.process_depth}"
    )

    print("[API] Step 3/4: Running loss breakdown procedure")
    result = RUN_LOSS_BREAKDOWN(
        env_overrides=env_overrides,
        max_depth=request.max_depth,
        process_depth=request.process_depth,
    )
    print("[API] Step 4/4: Procedure completed")

    return result


def _print_startup_banner(host: str, port: int) -> None:
    local_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    base_url = f"http://{local_host}:{port}"

    print("\n" + "=" * 72)
    print("Loss Breakdown API Service")
    print("=" * 72)
    print(f"Environment      : {ENV_PATH if ENV_PATH.exists() else 'No .env file found'}")
    print(f"Bind Address     : {host}:{port}")
    print(f"Base URL         : {base_url}")
    print("Docs             :")
    print(f"  Swagger UI     : {base_url}/docs")
    print(f"  ReDoc          : {base_url}/redoc")
    print(f"  OpenAPI JSON   : {base_url}/openapi.json")
    print("Endpoints        :")
    print(f"  GET  /health")
    print(f"  POST /run/main-asset/{{main_asset_id}}?max_depth=3&process_depth=3")
    print("Example          :")
    print(
        f"  curl -X POST \"{base_url}/run/main-asset/78fda490-e08b-11f0-b68f-8f33a9d74e0c\""
    )
    print("=" * 72 + "\n")


app = FastAPI(title="Loss Breakdown Service", version="1.1.0")

if not callable(RUN_LOSS_BREAKDOWN):
    raise RuntimeError(
        "API backend could not be loaded from 'Loss Breakdown.py'. "
        "Ensure run_loss_breakdown is defined."
    )


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/run/main-asset/{main_asset_id}")
def run_for_main_asset(main_asset_id: str, max_depth: int = 3, process_depth: int = 3) -> Dict[str, Any]:
    print("[API] Received request: /run/main-asset/{main_asset_id}")
    request = RunRequest(main_asset_id=main_asset_id, max_depth=max_depth, process_depth=process_depth)
    try:
        return _run_service(request)
    except Exception as exc:
        print(f"[API] Request failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    if uvicorn is None:
        raise RuntimeError(
            "uvicorn is not available. Install requirements first. "
            f"Import error: {UVICORN_IMPORT_ERROR}"
        )

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    _print_startup_banner(host=host, port=port)
    uvicorn.run(app, host=host, port=port)
