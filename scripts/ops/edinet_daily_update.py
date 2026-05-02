#!/usr/bin/env python3
"""毎営業日に実行するEDINET日次更新ラッパー。

祝日判定（jpholiday）を行い、営業日のみ bulk_download_edinet.py を起動する。
cron から呼び出すことを想定:
  30 18 * * 1-5 /home/k/projects/ir-monitoring-2nd/scripts/ops/edinet_daily_update.py
"""

from __future__ import annotations

import logging
import subprocess
import sys
from datetime import date
from pathlib import Path

try:
    import jpholiday
except ImportError:
    print("jpholiday not installed. Run: pip install jpholiday", file=sys.stderr)
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_FILE = PROJECT_ROOT / "logs" / "edinet_daily.log"
VENV_PYTHON = PROJECT_ROOT / "venv" / "bin" / "python"
BULK_SCRIPT = PROJECT_ROOT / "scripts" / "ops" / "bulk_download_edinet.py"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def is_business_day(d: date) -> bool:
    """平日かつ日本の祝日でない日を営業日とみなす。"""
    return d.weekday() < 5 and not jpholiday.is_holiday(d)


def main() -> None:
    today = date.today()
    logger.info("=== edinet_daily_update 開始: %s ===", today)

    if not is_business_day(today):
        logger.info("本日は非営業日のためスキップ: %s (weekday=%d, holiday=%s)",
                    today, today.weekday(), jpholiday.is_holiday(today))
        return

    logger.info("営業日確認 OK。bulk_download_edinet.py を実行します。")

    date_str = today.isoformat()
    cmd = [
        str(VENV_PYTHON),
        str(BULK_SCRIPT),
        "--start", date_str,
        "--end", date_str,
    ]
    logger.info("実行コマンド: %s", " ".join(cmd))

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=False,  # stdout/stderr をそのままログファイルに出力
    )

    if result.returncode == 0:
        logger.info("=== 正常終了: returncode=%d ===", result.returncode)
    else:
        logger.error("=== 異常終了: returncode=%d ===", result.returncode)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
