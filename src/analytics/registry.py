"""スクリーナーの自動発見・登録機構."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import TYPE_CHECKING, Dict, Type

if TYPE_CHECKING:
    from src.analytics.screeners._base import BaseScreener

logger = logging.getLogger(__name__)

_registry: Dict[str, Type[BaseScreener]] = {}


def register(name: str):
    """スクリーナーを登録するデコレータ.

    使用例:
        @register("eps_growth")
        class EPSGrowthScreener(BaseScreener):
            ...

    Args:
        name: スクリーナーの一意な名前

    Returns:
        クラスデコレータ
    """

    def decorator(cls: Type[BaseScreener]) -> Type[BaseScreener]:
        if name in _registry:
            logger.warning("Overwriting screener: %s", name)
        _registry[name] = cls
        return cls

    return decorator


def get_screener(name: str) -> Type[BaseScreener]:
    """名前でスクリーナークラスを取得.

    Args:
        name: スクリーナー名

    Returns:
        スクリーナークラス

    Raises:
        KeyError: 未登録のスクリーナー名の場合
    """
    if name not in _registry:
        available = ", ".join(sorted(_registry.keys()))
        raise KeyError(f"Unknown screener: {name}. Available: {available}")
    return _registry[name]


def list_screeners() -> list[str]:
    """登録済みスクリーナー名一覧.

    Returns:
        ソートされたスクリーナー名のリスト
    """
    return sorted(_registry.keys())


def auto_discover() -> None:
    """screeners/ 配下のモジュールを自動インポートして登録.

    アプリケーション起動時に一度だけ呼び出す。
    サブディレクトリ（growth/, value/ 等）も再帰的にスキャンする。
    """
    from src.analytics import screeners

    for _, name, _ in pkgutil.walk_packages(
        screeners.__path__,
        screeners.__name__ + ".",
    ):
        try:
            importlib.import_module(name)
        except ImportError as e:
            logger.warning("Failed to import screener module %s: %s", name, e)


def clear_registry() -> None:
    """レジストリをクリアする（テスト用）."""
    _registry.clear()


