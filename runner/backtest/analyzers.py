"""
回测分析器 - 扩展 backtrader 分析功能
"""

import backtrader as bt
import pandas as pd
from typing import Dict, Any


class BacktestAnalyzer:
    """
    回测分析器

    提供更详细的回测统计分析
    """

    def __init__(self):
        self.trades = []
        self.equity_curve = []

    def add_trade(self, trade: Dict[str, Any]):
        """添加交易记录"""
        self.trades.append(trade)

    def add_equity(self, equity: float):
        """添加净值记录"""
        self.equity_curve.append(equity)

    def calculate_stats(self) -> Dict[str, Any]:
        """计算统计指标"""
        if not self.trades:
            return {}

        df = pd.DataFrame(self.trades)

        stats = {
            'total_trades': len(df),
            'won_trades': len(df[df['pnl'] > 0]),
            'lost_trades': len(df[df['pnl'] <= 0]),
        }

        if stats['total_trades'] > 0:
            stats['win_rate'] = stats['won_trades'] / stats['total_trades'] * 100
        else:
            stats['win_rate'] = 0

        # 盈亏统计
        if 'pnl' in df.columns:
            stats['total_pnl'] = df['pnl'].sum()
            stats['avg_win'] = df[df['pnl'] > 0]['pnl'].mean() if len(df[df['pnl'] > 0]) > 0 else 0
            stats['avg_loss'] = df[df['pnl'] < 0]['pnl'].mean() if len(df[df['pnl'] < 0]) > 0 else 0

            if stats['avg_loss'] != 0:
                stats['profit_factor'] = abs(stats['avg_win'] / stats['avg_loss'])
            else:
                stats['profit_factor'] = float('inf')

        # 净值统计
        if self.equity_curve:
            equity = pd.Series(self.equity_curve)
            stats['max_equity'] = equity.max()
            stats['min_equity'] = equity.min()

            # 计算最大回撤
            peak = equity.expanding(min_periods=1).max()
            drawdown = (equity - peak) / peak * 100
            stats['max_drawdown'] = drawdown.min()

        return stats

    def generate_summary(self) -> str:
        """生成摘要报告"""
        stats = self.calculate_stats()

        lines = [
            "=" * 50,
            "回测统计摘要",
            "=" * 50,
            f"总交易次数: {stats.get('total_trades', 0)}",
            f"盈利交易: {stats.get('won_trades', 0)}",
            f"亏损交易: {stats.get('lost_trades', 0)}",
            f"胜率: {stats.get('win_rate', 0):.2f}%",
            "-" * 50,
            f"总盈亏: {stats.get('total_pnl', 0):.2f}",
            f"平均盈利: {stats.get('avg_win', 0):.2f}",
            f"平均亏损: {stats.get('avg_loss', 0):.2f}",
            f"盈亏比: {stats.get('profit_factor', 0):.2f}",
            "-" * 50,
            f"最大回撤: {stats.get('max_drawdown', 0):.2f}%",
            "=" * 50,
        ]

        return "\n".join(lines)


class PerformanceMetrics(bt.Analyzer):
    """性能指标分析器"""

    def __init__(self):
        self.rets = []
        self.prices = []

    def next(self):
        self.prices.append(self._owner.data.close[0])

        if len(self.prices) > 1:
            ret = (self.prices[-1] / self.prices[-2]) - 1
            self.rets.append(ret)

    def get_analysis(self):
        if not self.rets:
            return {}

        import numpy as np

        rets = np.array(self.rets)
        prices = np.array(self.prices)

        # 年化收益率
        annual_return = np.mean(rets) * 252 * 100

        # 年化波动率
        annual_vol = np.std(rets) * np.sqrt(252) * 100

        # 夏普比率 (假设无风险利率为0)
        sharpe = annual_return / annual_vol if annual_vol > 0 else 0

        # 最大回撤
        peak = np.maximum.accumulate(prices)
        drawdown = (prices - peak) / peak * 100
        max_dd = np.min(drawdown)

        return {
            'annual_return': annual_return,
            'annual_volatility': annual_vol,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
        }
