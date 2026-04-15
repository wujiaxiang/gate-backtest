"""
回测模块
========
使用 Backtrader 适配器运行回测
"""

from .engine import BacktestEngine, backtest

__all__ = ['BacktestEngine', 'backtest']
