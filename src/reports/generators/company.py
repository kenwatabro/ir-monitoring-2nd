"""銘柄別レポートの生成."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from src.query.repositories.company import CompanyRepository
from src.query.timeseries import get_financial_history
from src.reports.formatters._base import BaseFormatter
from src.reports.formatters.console import ConsoleFormatter

if TYPE_CHECKING:
    pass


class CompanyReportGenerator:
    """銘柄別レポートを生成.

    証券コードを指定して、財務推移レポートを生成する。

    Example:
        >>> generator = CompanyReportGenerator()
        >>> report = generator.generate("7203", years=5)
        >>> print(report)
    """

    def __init__(
        self,
        formatter: BaseFormatter | None = None,
        dsn: Optional[str] = None,
    ):
        """Initialize generator.

        Args:
            formatter: 出力フォーマッター（デフォルト: ConsoleFormatter）
            dsn: PostgreSQL 接続文字列（省略時は環境変数から取得）
        """
        self.formatter = formatter or ConsoleFormatter()
        self.dsn = dsn

    def generate(self, ticker: str, years: int = 5) -> str:
        """銘柄の財務推移レポートを生成.

        Args:
            ticker: 証券コード（例: "7203"）
            years: 取得する年数（デフォルト: 5年）

        Returns:
            フォーマットされたレポート文字列
        """
        # 会社名を取得
        company_repo = CompanyRepository(self.dsn)
        company = company_repo.find_by_ticker(ticker)
        company_name = company.name_jp if company else ticker

        # 財務データを取得
        history = get_financial_history(ticker, years=years, dsn=self.dsn)

        # フォーマットして返す
        return self.formatter.format(history, company_name=company_name)

    def generate_by_edinet_code(self, edinet_code: str, years: int = 5) -> str:
        """EDINETコードで銘柄の財務推移レポートを生成.

        Args:
            edinet_code: EDINETコード
            years: 取得する年数（デフォルト: 5年）

        Returns:
            フォーマットされたレポート文字列
        """
        from src.query.timeseries import get_financial_history_by_edinet_code

        # 会社名を取得
        company_repo = CompanyRepository(self.dsn)
        company = company_repo.find_by_edinet_code(edinet_code)
        company_name = company.name_jp if company else edinet_code

        # 財務データを取得
        history = get_financial_history_by_edinet_code(
            edinet_code, years=years, dsn=self.dsn
        )

        # フォーマットして返す
        return self.formatter.format(history, company_name=company_name)


