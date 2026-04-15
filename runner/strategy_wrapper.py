"""
策略包装器
==========
将 UserStrategy 包装为 Backtrader Strategy:

    - 桥接 Backtrader 的 next 调用到用户策略的逻辑
    - 统计交易盈亏与胜负
    - 记录权益曲线
"""

import backtrader as bt
import pandas as pd
import numpy as np
import talib
from typing import Optional


class UserStrategyWrapper(bt.Strategy):
    """
    用户策略包装器 - 马丁格尔加仓策略

    负责:
        - 桥接 next() 到马丁格尔逻辑
        - 统计每笔交易盈亏
        - 记录权益曲线
    """

    params = dict(
        # 杠杆
        leverage=50,

        # 止盈止损
        take_profit=0.25,
        stop_loss=0.25,

        # 马丁格尔阶梯阈值 (%)
        ladder_threshold_0=0.0,
        ladder_threshold_1=0.7,
        ladder_threshold_2=0.9,
        ladder_threshold_3=1.1,
        ladder_threshold_4=1.2,
        ladder_threshold_5=1.3,
        ladder_threshold_6=1.5,
        ladder_threshold_7=1.8,

        # 马丁格尔阶梯倍数
        ladder_mult_0=1,
        ladder_mult_1=2,
        ladder_mult_2=4,
        ladder_mult_3=8,
        ladder_mult_4=16,
        ladder_mult_5=32,
        ladder_mult_6=64,
        ladder_mult_7=128,

        # 动态系数范围
        coef_min=1.0,
        coef_max=2.0,

        # 止盈范围
        tp_min=0.005,
        tp_max=0.02,

        # 技术指标周期
        rsi_period=14,
        atr_period=14,

        # 利润复投比例
        compounding_ratio=0.3,

        # 方向
        direction='short',

        # 市场信息
        market='ETH_USDT',
        interval='1d',
    )

    def __init__(self):
        # 构建马丁格尔阶梯
        raw_thresholds = [
            self.params.ladder_threshold_0,
            self.params.ladder_threshold_1,
            self.params.ladder_threshold_2,
            self.params.ladder_threshold_3,
            self.params.ladder_threshold_4,
            self.params.ladder_threshold_5,
            self.params.ladder_threshold_6,
            self.params.ladder_threshold_7,
        ]
        raw_multipliers = [
            self.params.ladder_mult_0,
            self.params.ladder_mult_1,
            self.params.ladder_mult_2,
            self.params.ladder_mult_3,
            self.params.ladder_mult_4,
            self.params.ladder_mult_5,
            self.params.ladder_mult_6,
            self.params.ladder_mult_7,
        ]
        self.ladder = [
            (th / 100.0, mult) for th, mult in zip(raw_thresholds, raw_multipliers)
        ]

        # 状态变量
        self.current_ladder_step = 0
        self.entry_price = 0.0
        self.total_quantity = 0.0
        self.base_quantity = 0.0
        self.current_investment = 200  # 固定初始本金

        # 保证金比例
        self.margin_ratio_mult = 0.5

        # 交易统计
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        self.trade_pnls = []

        # 权益曲线
        self._equity_curve = []

        # 初始资金
        self.broker_start_value = None

        # 当前订单
        self._current_order = None

    def start(self):
        """策略开始，记录初始资金"""
        self.broker_start_value = self.broker.getvalue()

    def get_klines(self, limit: int = 50, as_df: bool = True):
        """
        获取 K线数据

        Args:
            limit: 获取最近 limit 根 K线
            as_df: 是否返回 DataFrame

        Returns:
            DataFrame 或 list
        """
        idx = len(self)
        if idx <= 0:
            return None

        use = min(limit + 1, idx)
        rows = []
        for i in range(idx - use + 1, idx + 1):
            try:
                dt = self.data.datetime[i]
                if dt != dt:  # NaN check
                    continue
                rows.append({
                    'time': int(dt),
                    'open': float(self.data.open[i]),
                    'high': float(self.data.high[i]),
                    'low': float(self.data.low[i]),
                    'close': float(self.data.close[i]),
                    'volume': float(self.data.volume[i]) if hasattr(self.data, 'volume') else 0.0,
                })
            except Exception:
                continue

        if not rows:
            return None

        if as_df:
            df = pd.DataFrame(rows)
            df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
            return df
        return rows

    def calculate_dynamic_coef(self, rsi_val: float, atr_val: float, price: float) -> float:
        """计算动态系数"""
        trend_factor = max(0.0, min(1.0, (rsi_val - 30.0) / 40.0))
        atr_pct = atr_val / price if price > 0 else 0.01
        vol_factor = min(1.0, atr_pct * 10)
        combined = (trend_factor + vol_factor) / 2
        coef = self.params.coef_min + combined * (self.params.coef_max - self.params.coef_min)
        return max(self.params.coef_min, min(self.params.coef_max, coef))

    def calculate_tp_by_step(self, step: int) -> float:
        """根据阶梯计算止盈阈值"""
        max_steps = len(self.ladder) - 1
        if max_steps <= 0:
            return self.params.tp_min
        ratio = min(1.0, step / max_steps)
        return self.params.tp_min + ratio * (self.params.tp_max - self.params.tp_min)

    def update_average_entry(self, new_price: float, new_quantity: float):
        """更新平均入场价"""
        new_cost = new_price * new_quantity
        total_cost_before = self.entry_price * self.total_quantity
        self.total_quantity += new_quantity
        if self.total_quantity > 0:
            self.entry_price = (total_cost_before + new_cost) / self.total_quantity

    def calculate_and_compound_pnl(self, close_price: float):
        """计算盈亏并复投"""
        if self.total_quantity <= 0 or self.entry_price <= 0:
            return

        pnl = (self.entry_price - close_price) * self.total_quantity

        if pnl > 0:
            investment_add = pnl * self.params.compounding_ratio
            self.current_investment += investment_add
        else:
            min_investment = 200 * 0.1
            self.current_investment = max(min_investment, self.current_investment + pnl)

    def reset_position(self):
        """重置仓位状态"""
        self.current_ladder_step = 0
        self.entry_price = 0.0
        self.total_quantity = 0.0
        self.base_quantity = 0.0
        self.margin_ratio_mult = 0.5

    def next(self):
        """Backtrader 主循环"""
        # 跳过待处理订单
        if self._current_order and not self._current_order.status == self._current_order.Completed:
            return

        # 跳过无效价格
        try:
            price = self.data.close[0]
            if price != price:  # NaN check
                return
        except Exception:
            return

        # 记录权益曲线
        value = self.broker.getvalue()
        dt = bt.num2date(self.data.datetime[0])
        self._equity_curve.append({
            'time': dt,
            'close': price,
            'fund': value,
            'position_size': self.position.size,
        })

        # 获取 K线数据
        df = self.get_klines(limit=50, as_df=True)
        if df is None or df.empty or len(df) < self.params.rsi_period + 5:
            return

        c = pd.to_numeric(df["close"], errors="coerce")
        if c.isna().any():
            return

        price = c.iloc[-1]
        if price != price:
            return

        # 计算 RSI 和 ATR
        close_arr = np.ascontiguousarray(c.values, dtype=np.float64)
        high_arr = np.ascontiguousarray(pd.to_numeric(df["high"], errors="coerce").values, dtype=np.float64)
        low_arr = np.ascontiguousarray(pd.to_numeric(df["low"], errors="coerce").values, dtype=np.float64)

        rsi_arr = talib.RSI(close_arr, timeperiod=max(2, self.params.rsi_period))
        atr_arr = talib.ATR(high_arr, low_arr, close_arr, timeperiod=max(2, self.params.atr_period))

        rsi_val = rsi_arr[-1] if not np.isnan(rsi_arr[-1]) else 50.0
        atr_val = atr_arr[-1] if not np.isnan(atr_arr[-1]) else price * 0.01

        dyn_coef = self.calculate_dynamic_coef(rsi_val, atr_val, price)

        # 检查持仓状态
        has_position = self.position.size != 0

        if not has_position:
            # 开仓
            sum_mult = sum(m for _, m in self.ladder)
            nominal_value = (self.current_investment / 2) * self.params.leverage
            self.base_quantity = nominal_value / sum_mult / price
            self.total_quantity = self.base_quantity
            self.entry_price = price
            self.current_ladder_step = 0
            self.margin_ratio_mult = 0.5

            self._current_order = self.sell(size=self.base_quantity)
            return

        # 持仓管理
        pnl_ratio = (self.entry_price - price) / self.entry_price if self.entry_price > 0 else 0

        # 止盈
        target_tp = self.calculate_tp_by_step(self.current_ladder_step)
        if pnl_ratio >= target_tp:
            self.calculate_and_compound_pnl(price)
            self._current_order = self.close()
            self.reset_position()
            return

        # 止损
        if pnl_ratio <= -self.params.stop_loss:
            self.calculate_and_compound_pnl(price)
            self._current_order = self.close()
            self.reset_position()
            return

        # 马丁格尔加仓
        if pnl_ratio < 0:
            loss_ratio = -pnl_ratio
            next_step = self.current_ladder_step + 1
            if next_step < len(self.ladder):
                threshold, mult = self.ladder[next_step]
                adjusted_threshold = threshold * dyn_coef

                if loss_ratio >= adjusted_threshold:
                    new_quantity = self.base_quantity * mult
                    self.update_average_entry(price, new_quantity)
                    self.current_ladder_step = next_step
                    self.margin_ratio_mult = (self.total_quantity * price) / (2 * self.current_investment)

                    self._current_order = self.sell(size=new_quantity)

    def notify_order(self, order):
        """订单通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            self._current_order = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self._current_order = None

    def notify_trade(self, trade):
        """交易完成回调：统计每笔盈亏与胜负"""
        if trade.isclosed:
            pnl = trade.pnlcomm
            self.trade_pnls.append(pnl)
            self.trade_count += 1

            if pnl > 0:
                self.win_count += 1
            elif pnl < 0:
                self.loss_count += 1

    def get_equity_curve(self):
        """获取权益曲线"""
        return self._equity_curve

    def stop(self):
        """策略结束"""
        pass
