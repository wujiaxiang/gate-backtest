"""
用户策略 - 马丁格尔加仓策略
继承 GateStrategy 风格接口
"""

import numpy as np
import pandas as pd
import talib


class UserStrategy:
    """
    马丁格尔加仓量化策略

    特性:
    - 马丁格尔加仓: 基于亏损比例的多阶梯加仓
    - 动态止盈止损: 根据市场波动调整阈值
    - 利润复投: 30%盈利自动滚入投资本金
    - 动态参数: 基于RSI和ATR调整策略参数
    """

    params = dict(
        settle="usdt",
        market="ETH_USDT",
        interval="1d",
        leverage=50,
        investment=200,
        commission=0.0002,
        take_profit=0.25,
        stop_loss=0.25,
        direction="short",

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
    )

    def __init__(self):
        self.order = None

        # 参数访问辅助 (兼容 backtrader params 和普通 dict)
        self._params = self.params.copy() if isinstance(self.params, dict) else {}

        # 构建马丁格尔阶梯
        raw_thresholds = [
            self._params.get('ladder_threshold_0', 0.0),
            self._params.get('ladder_threshold_1', 0.7),
            self._params.get('ladder_threshold_2', 0.9),
            self._params.get('ladder_threshold_3', 1.1),
            self._params.get('ladder_threshold_4', 1.2),
            self._params.get('ladder_threshold_5', 1.3),
            self._params.get('ladder_threshold_6', 1.5),
            self._params.get('ladder_threshold_7', 1.8),
        ]
        raw_multipliers = [
            self._params.get('ladder_mult_0', 1),
            self._params.get('ladder_mult_1', 2),
            self._params.get('ladder_mult_2', 4),
            self._params.get('ladder_mult_3', 8),
            self._params.get('ladder_mult_4', 16),
            self._params.get('ladder_mult_5', 32),
            self._params.get('ladder_mult_6', 64),
            self._params.get('ladder_mult_7', 128),
        ]
        self.ladder = [
            (th / 100.0, mult) for th, mult in zip(raw_thresholds, raw_multipliers)
        ]

        # 状态变量
        self.current_ladder_step = 0
        self.entry_price = 0.0
        self.total_quantity = 0.0
        self.base_quantity = 0.0
        self.current_investment = self._params.get('investment', 200)

    @property
    def p(self):
        """兼容 backtrader 的 params 访问方式"""
        return self._params

    def _get(self, key, default=None):
        """安全获取参数"""
        return self._params.get(key, default)

    def calculate_dynamic_coef(self, rsi_val: float, atr_val: float, price: float) -> float:
        """计算动态系数"""
        # RSI 趋势因子
        if rsi_val == rsi_val:
            trend_factor = max(0.0, min(1.0, (rsi_val - 30.0) / 40.0))
        else:
            trend_factor = 0.5

        # ATR 波动因子
        if atr_val == atr_val and price > 0:
            atr_pct = atr_val / price
            vol_factor = min(1.0, atr_pct * 10)
        else:
            vol_factor = 0.5

        combined = (trend_factor + vol_factor) / 2
        coef_min = self._params.get('coef_min', 1.0)
        coef_max = self._params.get('coef_max', 2.0)
        coef = coef_min + combined * (coef_max - coef_min)
        return max(coef_min, min(coef_max, coef))

    def calculate_tp_by_step(self, step: int) -> float:
        """根据阶梯计算止盈阈值"""
        max_steps = len(self.ladder) - 1
        if max_steps <= 0:
            return self._params.get('tp_min', 0.005)
        ratio = min(1.0, step / max_steps)
        tp_min = self._params.get('tp_min', 0.005)
        tp_max = self._params.get('tp_max', 0.02)
        tp = tp_min + ratio * (tp_max - tp_min)
        return tp

    def update_average_entry(self, new_price: float, new_quantity: float):
        """更新平均入场价"""
        new_cost = new_price * new_quantity
        total_cost_before = self.entry_price * self.total_quantity
        total_quantity_after = self.total_quantity + new_quantity
        if total_quantity_after > 0:
            self.entry_price = (total_cost_before + new_cost) / total_quantity_after
        else:
            self.entry_price = new_price
        self.total_quantity = total_quantity_after

    def calculate_and_compound_pnl(self, close_price: float):
        """计算盈亏并复投"""
        if self.total_quantity <= 0 or self.entry_price <= 0:
            return

        # 计算空头仓位盈亏
        pnl = (self.entry_price - close_price) * self.total_quantity
        compounding_ratio = self._params.get('compounding_ratio', 0.3)
        investment = self._params.get('investment', 200)

        if pnl > 0:
            # 盈利: 30% 加入投资本金
            investment_add = pnl * compounding_ratio
            self.current_investment += investment_add
            print(f"[COMPOUND] Profit={pnl:.4f} | Investment +{investment_add:.4f}={self.current_investment:.4f}")
        else:
            # 亏损: 从投资本金扣除
            min_investment = investment * 0.1
            new_investment = max(min_investment, self.current_investment + pnl)
            actual_loss = self.current_investment - new_investment
            print(f"[COMPOUND] Loss={pnl:.4f} | Investment -{actual_loss:.4f}={new_investment:.4f}")
            self.current_investment = new_investment

    def reset_position(self):
        """重置仓位状态"""
        self.current_ladder_step = 0
        self.entry_price = 0.0
        self.total_quantity = 0.0
        self.base_quantity = 0.0

    def next(self, get_klines_func, sell_func, close_func, position):
        """
        策略主逻辑 (Gate.io 风格)

        Args:
            get_klines_func: 获取K线数据的函数
            sell_func: 开仓函数
            close_func: 平仓函数
            position: 当前持仓对象
        """
        if self.order:
            return

        rsi_period = int(self._params.get('rsi_period', 14))
        atr_period = int(self._params.get('atr_period', 14))

        df = get_klines_func(limit=50, as_df=True)
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return
        if "c" not in df.columns or len(df) < max(2, rsi_period):
            return

        c = pd.to_numeric(df["c"], errors="coerce")
        if c.isna().any():
            return

        price = c.iloc[-1]
        if price != price:
            return

        # 计算技术指标
        if len(df) >= rsi_period + 5:
            close_arr = np.ascontiguousarray(c.values, dtype=np.float64)
            high_arr = np.ascontiguousarray(
                pd.to_numeric(df["h"], errors="coerce").values, dtype=np.float64
            ) if "h" in df.columns else close_arr
            low_arr = np.ascontiguousarray(
                pd.to_numeric(df["l"], errors="coerce").values, dtype=np.float64
            ) if "l" in df.columns else close_arr
            rsi_arr = talib.RSI(close_arr, timeperiod=max(2, rsi_period))
            atr_arr = talib.ATR(
                high_arr, low_arr, close_arr, timeperiod=max(2, atr_period)
            )
            rsi_val = rsi_arr[-1] if not np.isnan(rsi_arr[-1]) else 50.0
            atr_val = atr_arr[-1] if not np.isnan(atr_arr[-1]) else price * 0.01
        else:
            rsi_val, atr_val = 50.0, price * 0.01

        dyn_coef = self.calculate_dynamic_coef(rsi_val, atr_val, price)

        # 检查持仓状态
        has_position = position is not None and abs(position.size) > 1e-8
        leverage = self._params.get('leverage', 50)

        if not has_position:
            # 开仓
            sum_mult = 255
            nominal_value = (self.current_investment / 2) * leverage
            self.base_quantity = nominal_value / sum_mult / price
            self.total_quantity = self.base_quantity
            self.entry_price = price
            self.current_ladder_step = 0

            self.order = sell_func()
            print(f"[OPEN] First short | price={price:.2f} | qty={self.base_quantity:.4f} | lev={leverage} | coef={dyn_coef:.2f}")
            return

        if has_position and self.total_quantity > 0:
            pnl_ratio = (self.entry_price - price) / self.entry_price
            stop_loss = self._params.get('stop_loss', 0.25)

            # 检查止盈
            target_tp = self.calculate_tp_by_step(self.current_ladder_step)
            if pnl_ratio >= target_tp:
                self.calculate_and_compound_pnl(price)
                self.order = close_func()
                print(f"[TP] Take profit | price={price:.2f} | pnl={pnl_ratio:.4f} | target={target_tp:.4f} | step={self.current_ladder_step}")
                self.reset_position()
                return

            # 检查止损
            if pnl_ratio <= -stop_loss:
                self.calculate_and_compound_pnl(price)
                self.order = close_func()
                print(f"[SL] Stop loss | price={price:.2f} | pnl={pnl_ratio:.4f} | stop=-{stop_loss:.2f}")
                self.reset_position()
                return

            # 检查马丁格尔加仓
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

                        self.order = sell_func(size=new_quantity)
                        print(f"[ADD] Martingale | step={self.current_ladder_step} | price={price:.2f} | loss={loss_ratio:.4f} | mult={mult}")

    def notify_order(self, order):
        """订单通知回调"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f"[NOTIFY] Buy filled at {order.executed.price:.2f}")
            elif order.issell():
                print(f"[NOTIFY] Sell filled at {order.executed.price:.2f}")
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f"[NOTIFY] Order failed: {order.status}")
            self.order = None
