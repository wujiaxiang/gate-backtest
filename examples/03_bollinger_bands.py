"""
示例3: 布林带策略
-----------------
展示布林带指标的使用

策略逻辑:
- 价格触及下轨时买入
- 价格触及上轨时卖出
"""

import numpy as np
import pandas as pd
import talib


class UserStrategy:
    """
    布林带策略
    
    参数:
        bb_period: 布林带周期 (默认 20)
        bb_std: 标准差倍数 (默认 2.0)
    """
    
    params = dict(
        bb_period=20,
        bb_std=2.0,
    )
    
    def __init__(self):
        self.order = None
        
    def next(self, get_klines_func, sell_func, close_func, position):
        if self.order:
            return
        
        df = get_klines_func(limit=self.params['bb_period'] + 5, as_df=True)
        if df is None or len(df) < self.params['bb_period'] + 1:
            return
        
        close = pd.to_numeric(df["c"], errors="coerce").values
        high = pd.to_numeric(df["h"], errors="coerce").values
        low = pd.to_numeric(df["l"], errors="coerce").values
        
        # 计算布林带
        upper, middle, lower = talib.BBANDS(
            close, 
            timeperiod=self.params['bb_period'],
            nbdevup=self.params['bb_std'],
            nbdevdn=self.params['bb_std']
        )
        
        if np.isnan(upper[-1]) or np.isnan(lower[-1]):
            return
        
        current_price = close[-1]
        current_upper = upper[-1]
        current_lower = lower[-1]
        current_close = close[-1]
        
        # 交易逻辑
        if position.size == 0:
            # 价格触及下轨买入
            if low[-1] <= current_lower:
                self.order = sell_func(size=1)
        else:
            # 价格触及上轨卖出
            if high[-1] >= current_upper:
                self.order = close_func()
