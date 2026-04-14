"""
示例5: 马丁格尔策略 (进阶版)
---------------------------
展示马丁格尔加仓策略的实现

策略逻辑:
- 开仓后设置固定止盈止损
- 亏损时按倍数加仓摊平成本
- 盈利时平仓
"""

import numpy as np
import pandas as pd
import talib


class UserStrategy:
    """
    马丁格尔加仓策略
    
    特性:
    - 固定止盈止损比例
    - 亏损时按阶梯加仓
    - 支持做多/做空
    """
    
    params = dict(
        # 基础参数
        leverage=10,
        investment=100,
        
        # 止盈止损
        take_profit_pct=0.02,  # 2%
        stop_loss_pct=0.03,    # 3%
        
        # 方向: 'long' 或 'short'
        direction='long',
        
        # 马丁格尔参数
        ladder_step_1_pct=0.01,  # 1% 亏损时加仓
        ladder_step_2_pct=0.02,  # 2% 亏损时加仓
        ladder_mult_1=2,
        ladder_mult_2=4,
        
        # 技术指标
        rsi_period=14,
        rsi_entry=30,  # RSI < 30 时做多
    )
    
    def __init__(self):
        self.order = None
        
        # 状态变量
        self.entry_price = 0.0
        self.total_quantity = 0.0
        self.current_step = 0
        self.base_investment = self.params['investment']
        self.current_investment = self.base_investment
        
    def next(self, get_klines_func, sell_func, close_func, position):
        if self.order:
            return
        
        # 获取数据
        df = get_klines_func(limit=50, as_df=True)
        if df is None or len(df) < self.params['rsi_period'] + 5:
            return
        
        close = pd.to_numeric(df["c"], errors="coerce")
        high = pd.to_numeric(df["h"], errors="coerce")
        low = pd.to_numeric(df["l"], errors="coerce")
        
        current_price = close.iloc[-1]
        
        # 计算 RSI
        rsi = talib.RSI(close.values, timeperiod=self.params['rsi_period'])
        rsi_val = rsi[-1] if not np.isnan(rsi[-1]) else 50.0
        
        # 开仓逻辑
        if position.size == 0:
            if self.params['direction'] == 'long':
                # RSI 超卖时做多
                if rsi_val < self.params['rsi_entry']:
                    quantity = self.current_investment * self.params['leverage'] / current_price
                    self.order = sell_func(size=quantity)
                    self.entry_price = current_price
                    self.total_quantity = quantity
                    print(f"[开仓] 价格={current_price}, 数量={quantity:.4f}, RSI={rsi_val:.2f}")
        else:
            # 持仓管理
            if self.params['direction'] == 'long':
                pnl_pct = (current_price - self.entry_price) / self.entry_price
            else:
                pnl_pct = (self.entry_price - current_price) / self.entry_price
            
            # 检查止盈
            if pnl_pct >= self.params['take_profit_pct']:
                self.order = close_func()
                print(f"[止盈平仓] 价格={current_price}, 盈亏={pnl_pct*100:.2f}%")
                self._reset()
                return
            
            # 检查止损
            if pnl_pct <= -self.params['stop_loss_pct']:
                self.order = close_func()
                print(f"[止损平仓] 价格={current_price}, 盈亏={pnl_pct*100:.2f}%")
                self._reset()
                return
            
            # 马丁格尔加仓
            if self.params['direction'] == 'long':
                if pnl_pct <= -self.params['ladder_step_1_pct'] and self.current_step == 0:
                    self._add_position(current_price, self.params['ladder_mult_1'], sell_func)
                    self.current_step = 1
                elif pnl_pct <= -self.params['ladder_step_2_pct'] and self.current_step == 1:
                    self._add_position(current_price, self.params['ladder_mult_2'], sell_func)
                    self.current_step = 2
    
    def _add_position(self, price, multiplier, sell_func):
        """加仓"""
        additional = self.base_investment * multiplier * self.params['leverage'] / price
        self.total_quantity += additional
        self.current_investment = self.base_investment * (1 + sum([self.params['ladder_mult_1'], self.params['ladder_mult_2'][:self.current_step]]))
        self.order = sell_func(size=additional)
        print(f"[加仓] 价格={price}, 数量={additional:.4f}, 倍数={multiplier}x")
    
    def _reset(self):
        """重置状态"""
        self.entry_price = 0.0
        self.total_quantity = 0.0
        self.current_step = 0
        self.current_investment = self.base_investment
