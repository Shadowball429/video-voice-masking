import json
from logging import config, getLogger
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_CONFIG = BASE_DIR / "log_config.json"
_configured = False


def setup_logging(name: str | None = None):
    global _configured
    if not _configured:
        with LOG_CONFIG.open("r") as f:
            log_conf = json.load(f)

        file_handler = log_conf.get("handlers", {}).get("fileHandler", {})
        if file_handler:
            file_handler["filename"] = str(BASE_DIR / "info.log")

        config.dictConfig(log_conf)
        _configured = True

    return getLogger(name)
