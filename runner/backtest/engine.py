"""
回测引擎 - 基于 backtrader
"""

import backtrader as bt
import pandas as pd
from typing import Optional, Dict, Any, Type

from ..adapters.gatestrategy_adapter import GateStrategyAdapter, GateData
from ..data.fetcher import DataFetcher


class BacktestEngine:
    """
    回测引擎

    使用 backtrader 作为底层引擎，支持 Gate.io 风格策略
    """

    def __init__(
        self,
        strategy_class: Type,
        params: Dict[str, Any],
        initial_cash: float = 10000,
        commission: float = 0.0005
    ):
        """
        初始化回测引擎

        Args:
            strategy_class: 策略类
            params: 策略参数
            initial_cash: 初始资金
            commission: 手续费率
        """
        self.strategy_class = strategy_class
        self.params = params
        self.initial_cash = initial_cash
        self.commission = commission

        self._cerebro = None
        self._results = None

    def prepare_data(self, data: pd.DataFrame) -> GateData:
        """准备数据"""
        return GateData(dataname=data)

    def run(
        self,
        data: pd.DataFrame,
        plot: bool = False,
        output_dir: str = "results"
    ) -> Dict[str, Any]:
        """
        运行回测

        Args:
            data: K线数据
            plot: 是否绘制图表
            output_dir: 结果输出目录

        Returns:
            回测结果字典
        """
        # 创建 Cerebro 引擎
        self._cerebro = bt.Cerebro()

        # 设置初始资金
        self._cerebro.broker.setcash(self.initial_cash)

        # 设置手续费
        self._cerebro.broker.setcommission(commission=self.commission)

        # 添加数据
        data_feed = self.prepare_data(data)
        self._cerebro.adddata(data_feed)

        # 创建适配器策略
        class AdaptedStrategy(GateStrategyAdapter):
            pass

        # 添加策略
        self._cerebro.addstrategy(
            AdaptedStrategy,
            user_strategy_class=self.strategy_class
        )

        # 添加分析器
        self._cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self._cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self._cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        self._cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

        # 添加结果写入器
        import os
        os.makedirs(output_dir, exist_ok=True)
        self._cerebro.addwriter(
            bt.WriterFile,
            out=f'{output_dir}/trades.csv',
            csv=True
        )

        print(f"[回测] 初始资金: {self._cerebro.broker.getvalue():.2f} USDT")

        # 运行回测
        self._results = self._cerebro.run()

        # 获取结果
        final_value = self._cerebro.broker.getvalue()
        final_return = (final_value / self.initial_cash - 1) * 100

        print(f"[回测] 最终资金: {final_value:.2f} USDT")
        print(f"[回测] 总收益率: {final_return:.2f}%")

        # 提取分析数据
        result = self._extract_results(final_value)

        # 绘图
        if plot:
            self._cerebro.plot()

        return result

    def _extract_results(self, final_value: float) -> Dict[str, Any]:
        """提取分析结果"""
        result = {
            'initial_capital': self.initial_cash,
            'final_capital': final_value,
            'total_return': (final_value / self.initial_cash - 1),
            'return_pct': (final_value / self.initial_cash - 1) * 100,
        }

        if self._results:
            strat = self._results[0]

            # Sharpe Ratio
            sharpe = strat.analyzers.sharpe.get_analysis()
            result['sharpe_ratio'] = sharpe.get('sharperatio')

            # DrawDown
            dd = strat.analyzers.drawdown.get_analysis()
            result['max_drawdown'] = dd.get('max', {}).get('drawdown', 0)

            # Trade Analysis
            trades = strat.analyzers.trades.get_analysis()
            result['total_trades'] = trades.get('total', {}).get('total', 0)
            result['won_trades'] = trades.get('won', {}).get('total', 0)
            result['lost_trades'] = trades.get('lost', {}).get('total', 0)
            result['win_rate'] = (
                result['won_trades'] / result['total_trades'] * 100
                if result['total_trades'] > 0 else 0
            )

        return result

    def print_report(self, result: Dict[str, Any]):
        """打印回测报告"""
        print("\n" + "=" * 60)
        print("回测结果报告")
        print("=" * 60)

        print(f"初始资金: {result['initial_capital']:.2f} USDT")
        print(f"最终资金: {result['final_capital']:.2f} USDT")
        print(f"总收益率: {result['return_pct']:.2f}%")
        print("-" * 60)

        if result.get('total_trades', 0) > 0:
            print(f"总交易次数: {result['total_trades']}")
            print(f"盈利交易: {result['won_trades']}")
            print(f"亏损交易: {result['lost_trades']}")
            print(f"胜率: {result['win_rate']:.2f}%")
        print("-" * 60)

        if 'sharpe_ratio' in result:
            print(f"夏普比率: {result['sharpe_ratio']:.2f}" if result['sharpe_ratio'] else "夏普比率: N/A")
        if 'max_drawdown' in result:
            print(f"最大回撤: {result['max_drawdown']:.2f}%")

        print("=" * 60)
