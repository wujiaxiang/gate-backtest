"""
Gate 风格适配器
===============
将 Backtrader 接口桥接为 Gate.io 风格调用:

    - get_klines(limit, as_df) -> DataFrame
    - sell_func()/buy_func()/close_func() -> 提交订单
    - position -> 当前持仓对象 (提供 size/price 接口)
"""

import backtrader as bt
import pandas as pd
from typing import Optional


class GateAdapter:
    """
    Gate 风格接口适配器

    将 Backtrader 的数据源转换为 Gate 风格调用
    """

    def __init__(self, strategy: bt.Strategy):
        """
        初始化适配器

        Args:
            strategy: Backtrader 策略实例
        """
        self.strategy = strategy

    def get_klines(self, limit: int = 50, as_df: bool = True):
        """
        从 Backtrader 的数据源提取最近 limit 根K线，转换为 Gate 风格DataFrame

        Args:
            limit: 获取最近 limit 根 K线
            as_df: 是否返回 DataFrame

        Returns:
            DataFrame (列: time/open/high/low/close/volume) 或 list
        """
        data = self.strategy.datas[0]
        available = len(data)
        if available <= 0:
            return None

        use = min(limit, available)
        rows = []
        for i in range(-use, 0):
            try:
                dt = bt.num2date(data.datetime[i])
                ts = int(dt.timestamp() * 1000)
                rows.append({
                    'time': ts,
                    'open': float(data.open[i]),
                    'high': float(data.high[i]),
                    'low': float(data.low[i]),
                    'close': float(data.close[i]),
                    'volume': float(data.volume[i]) if hasattr(data, 'volume') else 0.0,
                })
            except Exception:
                continue

        if not rows:
            return None

        if as_df:
            df = pd.DataFrame(rows)
            return df
        return rows

    def sell_func(self, size: Optional[float] = None):
        """
        提交卖出（做空）订单

        Args:
            size: 开仓数量，None 则使用全仓默认

        Returns:
            Order 对象
        """
        if size is not None and size > 0:
            return self.strategy.sell(size=size)
        return self.strategy.sell()

    def buy_func(self, size: Optional[float] = None):
        """
        提交买入（做多）订单

        Args:
            size: 开仓数量，None 则使用全仓默认

        Returns:
            Order 对象
        """
        if size is not None and size > 0:
            return self.strategy.buy(size=size)
        return self.strategy.buy()

    def close_func(self):
        """
        平仓（根据当前方向自动选择 close）

        Returns:
            Order 对象
        """
        return self.strategy.close()

    @property
    def position(self):
        """
        返回 Backtrader 的持仓对象

        Returns:
            position 对象，具备 size/price 等属性
        """
        return self.strategy.position
