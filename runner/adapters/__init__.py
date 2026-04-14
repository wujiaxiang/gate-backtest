"""
适配器模块 - 桥接 GateStrategy 与 backtrader
"""

from .gatestrategy_adapter import GateStrategyAdapter, GateData

__all__ = ["GateStrategyAdapter", "GateData"]
