# ---------------------------------------------------------------------------
# __main__.py — Entry point: python -m src
# ---------------------------------------------------------------------------
import uvicorn

from src.config import load_config

if __name__ == "__main__":
    config = load_config()
    uvicorn.run(
        "src.app:app",
        host=config.host,
        port=config.port,
        reload=config.is_local,
        log_level=config.log_level.lower(),
    )
