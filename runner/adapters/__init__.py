"""
适配器层
========
提供 Backtrader 适配器，将 Backtrader 接口转换为 Gate 风格
"""

from .backtrader_adapter import BacktraderAdapter, create_engine
from .gate_adapter import GateAdapter

__all__ = ['BacktraderAdapter', 'create_engine', 'GateAdapter']
