"""
回测引擎
========
使用 Backtrader 适配器运行回测

使用方式:
    from runner.backtest import BacktestEngine
    from runner.strategies import UserStrategy

    engine = BacktestEngine()
    engine.set_data(df)
    engine.set_strategy(UserStrategy, **params)
    results = engine.run()
"""

import pandas as pd
from typing import Type, Optional, Dict, Any

from runner.adapters import BacktraderAdapter


class BacktestEngine:
    """
    回测引擎

    封装 Backtrader 适配器，提供简洁的 API
    """

    def __init__(
        self,
        cash: float = 200,
        commission: float = 0.0002,
        leverage: int = 50,
    ):
        """
        初始化回测引擎

        Args:
            cash: 初始资金
            commission: 手续费比例
            leverage: 杠杆倍数
        """
        self._adapter = BacktraderAdapter(
            cash=cash,
            commission=commission,
            leverage=leverage,
        )
        self._strategy_class = None
        self._strategy_params = {}
        self._data = None
        self._results = None

    def set_data(self, df: pd.DataFrame) -> 'BacktestEngine':
        """
        设置 K线数据

        Args:
            df: DataFrame，需包含 time/open/high/low/close/volume 列

        Returns:
            self
        """
        self._data = df
        self._adapter.add_data(df)
        return self

    def set_strategy(self, strategy_class: Type, **params) -> 'BacktestEngine':
        """
        设置策略

        Args:
            strategy_class: 策略类（使用 Gate 风格接口）
            **params: 策略参数

        Returns:
            self
        """
        self._strategy_class = strategy_class
        self._strategy_params = params
        return self

    def run(self, verbose: bool = True) -> 'BacktestEngine':
        """
        运行回测

        Args:
            verbose: 是否打印结果

        Returns:
            self
        """
        if self._strategy_class is None:
            raise ValueError("Strategy not set. Call set_strategy() first.")

        self._adapter.add_strategy(self._strategy_class, **self._strategy_params)
        self._results = self._adapter.run(verbose=verbose)
        return self

    def get_results(self) -> Dict[str, Any]:
        """获取回测结果"""
        if self._results is None:
            return {}
        return self._adapter.get_results(self._results[0])

    def get_equity_curve(self) -> list:
        """获取权益曲线"""
        if self._results is None:
            return []
        return self._adapter.get_equity_curve(self._results[0])

    def get_strategy(self):
        """获取策略实例"""
        if self._results is None:
            return None
        return self._results[0]

    def summary(self) -> str:
        """获取结果摘要"""
        result = self.get_results()
        if not result:
            return "No results"

        lines = [
            "=" * 50,
            "           BACKTEST SUMMARY",
            "=" * 50,
            f"Initial Cash:      {result.get('initial_cash', 0):>12.2f}",
            f"Final Value:       {result.get('final_value', 0):>12.2f}",
            f"Total Return:      {result.get('total_return', 0):>12.2f}%",
            "-" * 50,
            f"Sharpe Ratio:      {result.get('sharpe_ratio', 'N/A'):>12}",
            f"Max DrawDown:      {result.get('max_drawdown', 0):>12.2f}%",
            f"SQN:               {result.get('sqn', 'N/A'):>12}",
            "-" * 50,
            f"Total Trades:      {result.get('total_trades', 0):>12}",
            f"Win / Loss:        {result.get('won_trades', 0)} / {result.get('lost_trades', 0)}",
            f"Win Rate:          {result.get('win_rate', 0):>12.2f}%",
            f"Profit Factor:     {result.get('profit_factor', 0):>12.2f}",
            "=" * 50,
        ]
        return "\n".join(lines)


# 便捷函数
def backtest(
    df: pd.DataFrame,
    strategy_class: Type,
    cash: float = 200,
    commission: float = 0.0002,
    leverage: int = 50,
    **strategy_params
) -> BacktestEngine:
    """
    一行代码回测

    Args:
        df: K线数据
        strategy_class: 策略类
        cash: 初始资金
        commission: 手续费
        leverage: 杠杆
        **strategy_params: 策略参数

    Returns:
        BacktestEngine 实例
    """
    engine = BacktestEngine(cash=cash, commission=commission, leverage=leverage)
    engine.set_data(df)
    engine.set_strategy(strategy_class, **strategy_params)
    engine.run()
    return engine
