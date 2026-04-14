"""
示例2: 均线交叉策略
-------------------
进阶示例，展示多指标组合使用

策略逻辑:
- 金叉 (短期均线 > 长期均线) 时买入
- 死叉 (短期均线 < 长期均线) 时卖出
"""

import numpy as np
import pandas as pd
import talib


class UserStrategy:
    """
    均线交叉策略
    
    参数:
        fast_period: 快线周期 (默认 10)
        slow_period: 慢线周期 (默认 30)
    """
    
    params = dict(
        fast_period=10,
        slow_period=30,
    )
    
    def __init__(self):
        self.order = None
        self.last_fast = None
        self.last_slow = None
        
    def next(self, get_klines_func, sell_func, close_func, position):
        if self.order:
            return
        
        df = get_klines_func(limit=self.params['slow_period'] + 5, as_df=True)
        if df is None or len(df) < self.params['slow_period'] + 1:
            return
        
        close = pd.to_numeric(df["c"], errors="coerce").values
        
        # 计算均线
        fast_ma = talib.MA(close, timeperiod=self.params['fast_period'])
        slow_ma = talib.MA(close, timeperiod=self.params['slow_period'])
        
        if np.isnan(fast_ma[-1]) or np.isnan(slow_ma[-1]):
            return
        
        current_fast = fast_ma[-1]
        current_slow = slow_ma[-1]
        
        # 交易逻辑
        if position.size == 0:
            # 金叉买入
            if self.last_fast is not None and self.last_slow is not None:
                if self.last_fast <= self.last_slow and current_fast > current_slow:
                    self.order = sell_func(size=1)
        else:
            # 死叉卖出
            if self.last_fast is not None and self.last_slow is not None:
                if self.last_fast >= self.last_slow and current_fast < current_slow:
                    self.order = close_func()
        
        # 记录上根K线数据
        self.last_fast = current_fast
        self.last_slow = current_slow
