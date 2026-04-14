"""
示例1: 简单 RSI 策略
--------------------
一个最基础的策略示例，展示如何编写 user_strategy.py

策略逻辑:
- RSI < 30 时买入（超卖）
- RSI > 70 时卖出（超买）
- 仅做多，不做空
"""

import numpy as np
import pandas as pd
import talib


class UserStrategy:
    """
    简单 RSI 策略
    
    参数:
        rsi_period: RSI 计算周期 (默认 14)
        rsi_oversold: 超卖阈值 (默认 30)
        rsi_overbought: 超买阈值 (默认 70)
    """
    
    params = dict(
        rsi_period=14,
        rsi_oversold=30,
        rsi_overbought=70,
    )
    
    def __init__(self):
        self.order = None
        
    def next(self, get_klines_func, sell_func, close_func, position):
        """
        策略主逻辑
        
        Args:
            get_klines_func: 获取K线数据的函数，使用方式: df = get_klines_func(limit=100, as_df=True)
            sell_func: 开仓函数，使用方式: sell_func(size=数量)
            close_func: 平仓函数，使用方式: close_func()
            position: 当前持仓对象，使用方式: position.size 获取持仓数量
        """
        if self.order:
            return
        
        # 获取K线数据
        df = get_klines_func(limit=100, as_df=True)
        if df is None or len(df) < self.params['rsi_period'] + 5:
            return
        
        # 计算 RSI
        close = pd.to_numeric(df["c"], errors="coerce")
        rsi = talib.RSI(close.values, timeperiod=self.params['rsi_period'])
        rsi_val = rsi[-1] if not np.isnan(rsi[-1]) else 50.0
        
        # 交易逻辑
        if position.size == 0:
            # 无持仓，RSI 超卖时买入
            if rsi_val < self.params['rsi_oversold']:
                self.order = sell_func(size=1)  # 开多
        else:
            # 有持仓，RSI 超买时卖出
            if rsi_val > self.params['rsi_overbought']:
                self.order = close_func()
