"""
示例4: 网格策略
---------------
展示网格交易的思想

策略逻辑:
- 将价格分成N个网格
- 每个网格价位挂限价单
- 价格下跌时买入，上涨时卖出
"""

import numpy as np
import pandas as pd


class UserStrategy:
    """
    简单网格策略
    
    参数:
        grid_count: 网格数量 (默认 10)
        grid_size: 每个网格的持仓量 (默认 0.1)
    """
    
    params = dict(
        grid_count=10,
        grid_size=0.1,
    )
    
    def __init__(self):
        self.order = None
        self.grid_prices = []
        self.last_price = None
        self.initialized = False
        
    def next(self, get_klines_func, sell_func, close_func, position):
        if self.order:
            return
        
        df = get_klines_func(limit=2, as_df=True)
        if df is None or len(df) < 2:
            return
        
        close = pd.to_numeric(df["c"], errors="coerce")
        current_price = close.iloc[-1]
        
        # 初始化网格
        if not self.initialized:
            price_range = current_price * 0.1  # 10% 范围
            start_price = current_price - price_range / 2
            end_price = current_price + price_range / 2
            
            self.grid_prices = np.linspace(start_price, end_price, self.params['grid_count'])
            self.initialized = True
            print(f"[网格] 初始化: {self.grid_prices}")
        
        self.last_price = current_price
        
        # 检查是否触及网格
        for i, grid_price in enumerate(self.grid_prices):
            if abs(current_price - grid_price) < current_price * 0.005:  # 0.5% 容差
                # 价格触及网格
                if position.size == 0:
                    # 无持仓，网格买入
                    self.order = sell_func(size=self.params['grid_size'])
                    print(f"[网格] 买入 @ {current_price}, 数量 {self.params['grid_size']}")
                    break
                else:
                    # 有持仓，网格卖出
                    self.order = close_func()
                    print(f"[网格] 卖出 @ {current_price}")
                    break
