import math
import sys
import json
from logging import getLogger, config

# ログ出力設定参照
with open('log_config.json', 'r') as f:
    log_conf = json.load(f)

config.dictConfig(log_conf)

# ログ出力オブジェクト
logger = getLogger(__name__)


def main(val):
  val = float(val)
  logger.info(val)
  print(math.radians(val))

if __name__ == "__main__":
  main(sys.argv[1])
