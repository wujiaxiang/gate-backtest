"""
GateStrategy -> backtrader 适配器
将 Gate.io 风格策略转换为 backtrader 可执行格式
"""

import backtrader as bt
import pandas as pd
import numpy as np
from typing import Optional


class GateStrategyAdapter(bt.Strategy):
    """
    GateStrategy 适配器 - 桥接 Gate.io 策略到 backtrader

    用户策略继承此类，适配器会在 __init__ 中实例化用户策略并调用其方法
    """

    params = dict(
        user_strategy_class=None,  # 用户策略类
    )

    def __init__(self):
        self.order = None

        # 实例化用户策略
        user_strategy_class = self.p.user_strategy_class if hasattr(self.p, 'user_strategy_class') else None
        if user_strategy_class:
            try:
                self._user_strategy = user_strategy_class()

                # 如果用户策略有 _params 属性（我们定义的策略格式），更新它
                if hasattr(self._user_strategy, '_params'):
                    # 从 backtrader params 获取值
                    for param_name in dir(self.p):
                        if not param_name.startswith('_') and param_name != 'user_strategy_class':
                            try:
                                value = getattr(self.p, param_name)
                                self._user_strategy._params[param_name] = value
                            except Exception:
                                pass

                # 初始化持仓属性
                self._user_strategy.position = type('Position', (), {'size': 0})()
                self._user_strategy.order = None
                print(f"[适配器] 用户策略 {self._user_strategy.__class__.__name__} 初始化成功")
            except Exception as e:
                print(f"[适配器] 用户策略初始化失败: {e}")
                import traceback
                traceback.print_exc()
                self._user_strategy = None
        else:
            self._user_strategy = None

    def get_klines(self, limit: int = 50, as_df: bool = True) -> Optional[pd.DataFrame]:
        """
        获取历史K线数据 (模拟 GateStrategy 接口)

        Args:
            limit: 获取的K线数量
            as_df: 是否返回 DataFrame 格式

        Returns:
            DataFrame 格式的K线数据，或原始数据
        """
        if as_df:
            data_len = len(self.data)
            lookback = min(limit, data_len)

            if lookback <= 0:
                return None

            # 构建 DataFrame (Gate.io 格式: c=close, h=high, l=low, o=open, v=volume)
            df = pd.DataFrame({
                't': [i for i in range(data_len)],
                'o': [self.data.open[i] for i in range(data_len)],
                'h': [self.data.high[i] for i in range(data_len)],
                'l': [self.data.low[i] for i in range(data_len)],
                'c': [self.data.close[i] for i in range(data_len)],
                'v': [self.data.volume[i] for i in range(data_len)] if hasattr(self.data, 'volume') else [1.0] * data_len
            })
            return df
        else:
            return self.data

    def sell(self, size: float = None):
        """开空仓 (使用 backtrader 的 sell)"""
        # 调用父类的 sell 方法
        return super().sell(size=abs(size) if size else None)

    def close_position(self):
        """平仓 (使用 backtrader 的 close)"""
        return super().close()

    def notify_order(self, order):
        """订单通知回调"""
        if self._user_strategy and hasattr(self._user_strategy, 'notify_order'):
            # 转换 backtrader 订单状态为 Gate.io 风格
            status_map = {
                bt.Order.Submitted: 'Submitted',
                bt.Order.Accepted: 'Accepted',
                bt.Order.Completed: 'Completed',
                bt.Order.Canceled: 'Canceled',
                bt.Order.Margin: 'Margin',
                bt.Order.Rejected: 'Rejected'
            }

            wrapped_order = type('Order', (), {
                'status': status_map.get(order.status, 'Unknown'),
                'isbuy': lambda: order.isbuy(),
                'issell': lambda: order.issell(),
                'executed': type('Executed', (), {'price': order.executed.price})()
            })()

            if wrapped_order.status in ['Completed', 'Canceled', 'Margin', 'Rejected']:
                self._user_strategy.order = None
            else:
                self._user_strategy.order = wrapped_order

            try:
                self._user_strategy.notify_order(wrapped_order)
            except Exception as e:
                print(f"[通知回调错误] {e}")

        # backtrader 订单完成后清除
        if order.status == bt.Order.Completed:
            self.order = None

    def next(self):
        """K线/bar 推进时的回调"""
        if self._user_strategy:
            # 更新用户策略的持仓状态
            self._user_strategy.position.size = self.position.size

            # 调用用户策略的 next 方法（传入必要的函数引用）
            try:
                self._user_strategy.next(
                    get_klines_func=self.get_klines,
                    sell_func=self.sell,
                    close_func=self.close_position,
                    position=self.position
                )
            except TypeError as e:
                # 用户策略可能调用了 super().next()
                print(f"[策略执行] TypeError: {e}")
                pass
            except Exception as e:
                print(f"[策略执行错误] {e}")


class GateData(bt.feeds.PandasData):
    """
    Gate.io 格式的 K线数据

    列名: o(open), h(high), l(low), c(close), v(volume)
    """
    params = (
        ('datetime', None),
        ('open', 'o'),
        ('high', 'h'),
        ('low', 'l'),
        ('close', 'c'),
        ('volume', 'v'),
        ('openinterest', -1),
    )
