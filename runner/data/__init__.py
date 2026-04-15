"""
数据获取模块 - 支持多交易所 API 和 Gate.io 历史批量数据
"""

from .fetcher import DataFetcher
from .gate_histor import GateHistoricalDownloader

__all__ = ["DataFetcher", "GateHistoricalDownloader"]
