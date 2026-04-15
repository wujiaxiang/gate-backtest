"""
Backtrader 适配器
================
将 Backtrader 接口转换为 Gate.io 风格

策略层使用 Gate 风格接口:
    - get_klines_func(limit, as_df) -> DataFrame
    - sell_func(size) -> Order
    - close_func() -> Order
    - position.size -> float

适配器负责:
    - 数据格式转换
    - 订单撮合
    - 保证金/杠杆计算
    - 爆仓检测
"""

import backtrader as bt
import pandas as pd
import numpy as np
from typing import Callable, Any, Optional, Dict


class BacktraderAdapter:
    """
    Backtrader 适配器

    将 Backtrader 的 Cerebro/Broker 封装为 Gate 风格接口
    """

    def __init__(
        self,
        cash: float = 200,
        commission: float = 0.0002,
        leverage: int = 50,
    ):
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(cash)

        # 设置保证金模式: margin = 1/leverage
        self.cerebro.broker.setcommission(
            commission=commission,
            margin=1.0 / leverage,
            mult=leverage,
        )

        self._data = None
        self._strategy = None
        self._strategy_class = None
        self._strategy_params = {}

        # 持仓信息
        self._position_size = 0.0
        self._position_price = 0.0

    def add_data(self, df: pd.DataFrame) -> 'BacktraderAdapter':
        """
        添加 K线数据

        Args:
            df: DataFrame，需包含 time/open/high/low/close/volume 列

        Returns:
            self
        """
        df = df.copy()

        # 标准化列名
        if 'time' in df.columns:
            df.rename(columns={'time': 'datetime'}, inplace=True)
        if 'o' in df.columns:
            df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)

        # 确保 datetime 列
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)

        self._data = bt.feeds.PandasData(
            dataname=df,
            datetime=None,
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1
        )
        self.cerebro.adddata(self._data)

        return self

    def add_strategy(self, strategy_class, **params) -> 'BacktraderAdapter':
        """
        添加策略

        Args:
            strategy_class: 策略类（接受 Gate 风格接口）
            **params: 策略参数

        Returns:
            self
        """
        self._strategy_class = strategy_class
        self._strategy_params = params
        return self

    def add_analyzers(self) -> 'BacktraderAdapter':
        """添加标准分析器"""
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days)
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='dd')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='ta')
        self.cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        return self

    def run(self, verbose: bool = False) -> list:
        """
        运行回测

        Returns:
            回测结果列表
        """
        if self._strategy_class is None:
            raise ValueError("Strategy not set. Call add_strategy() first.")

        # 直接使用策略类，Backtrader 会自动处理 params
        self.cerebro.addstrategy(self._strategy_class, **self._strategy_params)
        self.add_analyzers()

        results = self.cerebro.run()

        if verbose:
            self._print_results(results[0])

        return results

    def _create_strategy_wrapper(self):
        """
        创建策略包装器

        将 Backtrader 的原生接口转换为 Gate 风格
        """

        class GateStrategyWrapper(self._strategy_class):
            """
            Gate 风格策略包装器

            将 Backtrader 的 self.data, self.buy(), self.sell() 等
            转换为策略期望的 get_klines_func, sell_func, close_func 接口
            """

            def __init__(inner):
                # 调用父类 __init__
                super().__init__()

                # Backtrader 内部状态
                inner._bt_cerebro = self.cerebro
                inner._bt_broker = self.cerebro.broker
                inner._bt_order = None
                inner._bt_position_size = 0.0
                inner._bt_position_price = 0.0

                # K线缓存（用于 get_klines_func）
                inner._klines_cache = []

                # 追踪历史状态
                inner._equity_curve = []
                inner._trades_log = []

            @property
            def position(inner):
                """模拟 Gate 风格的 position 对象"""
                class Position:
                    size = inner._bt_position_size
                    price = inner._bt_position_price
                return Position()

            def _get_klines(self, limit: int = 50, as_df: bool = True):
                """
                获取 K线数据（Gate 风格）

                返回最近 limit 根 K线
                """
                # 获取当前索引位置
                idx = len(self)

                # 从 Backtrader 数据源获取历史数据
                df_list = []
                lookback = min(limit, idx + 1)

                for i in range(idx - lookback + 1, idx + 1):
                    try:
                        dt = self.data.datetime[i]
                        o = self.data.open[i]
                        h = self.data.high[i]
                        l = self.data.low[i]
                        c = self.data.close[i]
                        v = self.data.volume[i]

                        df_list.append({
                            't': int(dt) if dt else 0,
                            'o': o if o == o else 0,
                            'h': h if h == h else 0,
                            'l': l if l == l else 0,
                            'c': c if c == c else 0,
                            'v': v if v == v else 0,
                        })
                    except:
                        break

                if as_df:
                    if not df_list:
                        return pd.DataFrame()
                    df = pd.DataFrame(df_list)
                    df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
                    return df
                return df_list

            def _sell_func(self, size: float = None):
                """
                开仓函数（Gate 风格）

                Args:
                    size: 开仓数量（None = 全仓）

                Returns:
                    Order 对象
                """
                if size is None or size <= 0:
                    # 全仓模式
                    cash = self._bt_broker.getcash()
                    price = self.data.close[0]
                    size = cash * self.p.get('leverage', 50) / price * 0.98  # 留点余量

                order = self.sell(size=size)
                self._bt_order = order
                return order

            def _close_func(self):
                """
                平仓函数（Gate 风格）
                """
                order = self.close()
                self._bt_order = order
                return order

            def next(inner):
                """主循环"""
                # 更新持仓状态
                inner._bt_position_size = inner.position.size
                inner._bt_position_price = inner.position.price

                # 跳过无效价格
                try:
                    price = inner.data.close[0]
                    if price != price:  # NaN
                        return
                except:
                    return

                # 调用原始策略的 next 方法
                # 传入 Gate 风格的接口
                try:
                    super(GateStrategyWrapper, inner).next(
                        get_klines_func=inner._get_klines,
                        sell_func=inner._sell_func,
                        close_func=inner._close_func,
                        position=inner.position
                    )
                except Exception as e:
                    # 策略执行错误时跳过
                    pass

                # 记录权益曲线
                value = inner._bt_broker.getvalue()
                inner._equity_curve.append({
                    'time': inner.data.datetime.date(0) if hasattr(inner.data.datetime, 'date') else None,
                    'close': price,
                    'position_size': inner._bt_position_size,
                    'fund': value,
                    'unrealized_pnl': inner.position.size * (price - inner._bt_position_price) if inner._bt_position_size else 0,
                })

            def notify_order(inner, order):
                """订单通知"""
                if order.status in [order.Submitted, order.Accepted]:
                    return

                if order.status == order.Completed:
                    if order.isbuy():
                        inner._bt_position_size = inner.position.size
                        inner._bt_position_price = inner.position.price
                    elif order.issell():
                        inner._bt_position_size = inner.position.size
                        inner._bt_position_price = inner.position.price

                inner._bt_order = None

            def get_equity_curve(inner):
                return inner._equity_curve

        return GateStrategyWrapper

    def _print_results(self, strategy):
        """打印回测结果"""
        result = self.get_results(strategy)
        print("\n" + "=" * 50)
        print("           BACKTEST SUMMARY")
        print("=" * 50)
        print(f"Initial Cash:      {result['initial_cash']:>12.2f}")
        print(f"Final Value:       {result['final_value']:>12.2f}")
        print(f"Total Return:      {result['total_return']:>12.2f}%")
        print("-" * 50)
        print(f"Sharpe Ratio:      {result.get('sharpe_ratio', 'N/A'):>12}")
        print(f"Max DrawDown:      {result.get('max_drawdown', 0):>12.2f}%")
        print(f"SQN:               {result.get('sqn', 'N/A'):>12}")
        print("-" * 50)
        print(f"Total Trades:      {result.get('total_trades', 0):>12}")
        print(f"Win / Loss:        {result.get('won_trades', 0)} / {result.get('lost_trades', 0)}")
        print(f"Win Rate:          {result.get('win_rate', 0):>12.2f}%")
        print(f"Profit Factor:     {result.get('profit_factor', 0):>12.2f}")
        print("=" * 50)

    def get_results(self, strategy) -> Dict[str, Any]:
        """获取回测结果"""
        result = {}

        # 资金信息
        result['initial_cash'] = self.cerebro.broker.startingcash
        result['final_value'] = self.cerebro.broker.getvalue()
        result['total_return'] = (result['final_value'] - result['initial_cash']) / result['initial_cash'] * 100

        # 分析器
        sharpe = strategy.analyzers.sharpe.get_analysis()
        result['sharpe_ratio'] = sharpe.get('sharperatio', None)

        dd = strategy.analyzers.dd.get_analysis()
        result['max_drawdown'] = dd.get('max', {}).get('drawdown', 0)

        ta = strategy.analyzers.ta.get_analysis()
        result['total_trades'] = ta.get('total', {}).get('total', 0)
        result['won_trades'] = ta.get('won', {}).get('total', 0)
        result['lost_trades'] = ta.get('lost', {}).get('total', 0)
        if result['total_trades'] > 0:
            result['win_rate'] = result['won_trades'] / result['total_trades'] * 100

        sqn = strategy.analyzers.sqn.get_analysis()
        result['sqn'] = sqn.get('sqn', None)

        return result

    def get_equity_curve(self, strategy) -> list:
        """获取权益曲线"""
        if hasattr(strategy, 'get_equity_curve'):
            return strategy.get_equity_curve()
        return []


def create_engine(
    cash: float = 200,
    commission: float = 0.0002,
    leverage: int = 50,
) -> BacktraderAdapter:
    """
    创建回测引擎

    便捷函数
    """
    return BacktraderAdapter(cash=cash, commission=commission, leverage=leverage)
