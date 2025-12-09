"""各種データソースからDBへロードする ETL/ingest 用パッケージ."""

from .edinet_loader import load_edinet_directory

__all__ = ["load_edinet_directory"]



