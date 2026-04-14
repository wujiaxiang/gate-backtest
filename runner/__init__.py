"""
Gate-Backtest Runner
====================
Gate.io 量化策略回测执行引擎

基于 backtrader + ccxt 构建，支持多交易所数据源
"""

__version__ = "0.1.0"
__author__ = "Claw"

from .backtest.engine import BacktestEngine
from .strategies.user_strategy import UserStrategy

__all__ = ["BacktestEngine", "UserStrategy"]
