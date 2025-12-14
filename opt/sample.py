import json
import math
import sys
from pathlib import Path
from logging import config, getLogger

# スクリプトの配置ディレクトリを基準にログ設定とログファイルを解決する
BASE_DIR = Path(__file__).resolve().parent
LOG_CONFIG = BASE_DIR / "log_config.json"

with LOG_CONFIG.open("r") as f:
    log_conf = json.load(f)

# ログファイルの出力先をスクリプトと同じディレクトリに固定する
file_handler = log_conf.get("handlers", {}).get("fileHandler", {})
if file_handler:
    file_handler["filename"] = str(BASE_DIR / "info.log")

config.dictConfig(log_conf)
logger = getLogger(__name__)


def main(val):
    val = float(val)
    logger.info(val)
    print(math.radians(val))


if __name__ == "__main__":
    main(sys.argv[1])
