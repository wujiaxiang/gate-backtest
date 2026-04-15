#!/usr/bin/env python3
"""
回测入口脚本
============
基于 Backtrader 的回测编排:

    - 支持本地 CSV/GZ 文件
    - 支持 CCXT 在线获取数据 (秒级/分钟级)
    - 配置 Cerebro、佣金、杠杆
    - 加载策略与 Gate 风格参数
    - 运行回测并输出标准化统计结果

使用方法:
    # 本地文件回测
    python backtest_runner.py --csv ./data.csv --cash 10000 --leverage 50
    python backtest_runner.py --csv ./ETH.csv.gz --from 2026-01-01 --to 2026-04-15

    # 在线获取数据回测 (CCXT)
    python backtest_runner.py --symbol ETH/USDT --exchange gateio --interval 1m --hours 24
    python backtest_runner.py --symbol BTC/USDT --exchange gateio --interval 1s --hours 2
"""

import os
import sys
import argparse
import json
import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import backtrader as bt

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runner.strategy_wrapper import UserStrategyWrapper as Strategy


# ==================== 数据加载 ====================

def load_local_data(csv_path: str) -> pd.DataFrame:
    """加载本地数据文件"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"文件不存在: {csv_path}")

    if csv_path.endswith('.gz'):
        # Gate.io 格式: timestamp, volume, open, high, low, close
        df = pd.read_csv(csv_path, compression='gzip', header=None)
        df.columns = ['timestamp', 'volume', 'open', 'high', 'low', 'close']
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    else:
        df = pd.read_csv(csv_path)
        if 'datetime' not in df.columns:
            df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']

    return df[['datetime', 'open', 'high', 'low', 'close', 'volume']]


def load_ccxt_data(
    symbol: str,
    exchange: str = 'gateio',
    interval: str = '1m',
    hours: int = 24,
    max_records: int = 100000,
) -> pd.DataFrame:
    """
    使用 CCXT 获取在线数据

    Args:
        symbol: 交易对，如 'ETH/USDT'
        exchange: 交易所，如 'gateio', 'binance'
        interval: 时间间隔，如 '1s', '1m', '5m', '1h'
        hours: 获取多少小时的数据
        max_records: 最大记录数
    """
    from runner.data.realtime_fetcher import ccxt_fetch_ohlcv

    df = ccxt_fetch_ohlcv(
        symbol=symbol,
        interval=interval,
        exchange=exchange,
        max_records=max_records,
        verbose=True,
    )

    if df.empty:
        raise ValueError(f"无法获取 {symbol} 数据")

    # 转换为标准格式
    if 'time' in df.columns:
        df = df.rename(columns={'time': 'datetime'})
    else:
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')

    # 确保datetime类型
    df['datetime'] = pd.to_datetime(df['datetime'])

    # 标准化列名 (保留原始格式给 Backtrader)
    result = df[['datetime', 'open', 'high', 'low', 'close', 'volume']].copy()

    return result


def filter_by_date(df: pd.DataFrame, date_from: str = None, date_to: str = None) -> pd.DataFrame:
    """按日期过滤数据"""
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])

    if date_from:
        df = df[df['datetime'] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df['datetime'] <= pd.to_datetime(date_to + ' 23:59:59')]

    return df


# ==================== 回测引擎 ====================

def run_backtest(
    df: pd.DataFrame,
    gate_params: dict,
    cash: float = 10000.0,
    commission: float = 0.0002,
    leverage: int = 1,
    slippage: float = 0.0,
    verbose: bool = True,
) -> dict:
    """运行回测"""
    cerebro = bt.Cerebro()

    # 资金与经纪配置
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=commission, margin=1.0 / leverage, mult=leverage)

    # 滑点
    if slippage and slippage > 0:
        cerebro.broker.set_slippage_perc(slippage)

    # 数据 - 确保datetime是datetime类型
    df_plot = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_plot['datetime']):
        df_plot['datetime'] = pd.to_datetime(df_plot['datetime'])

    data = bt.feeds.PandasData(
        dataname=df_plot,
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        openinterest=-1
    )
    cerebro.adddata(data)

    # 分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='dd')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='ta')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')

    # 策略
    cerebro.addstrategy(Strategy, **{
        'leverage': gate_params.get('leverage', leverage),
        'take_profit': gate_params.get('take_profit', 0.25),
        'stop_loss': gate_params.get('stop_loss', 0.25),
        'ladder_threshold_0': gate_params.get('ladder_threshold_0', 0.0),
        'ladder_threshold_1': gate_params.get('ladder_threshold_1', 0.7),
        'ladder_threshold_2': gate_params.get('ladder_threshold_2', 0.9),
        'ladder_threshold_3': gate_params.get('ladder_threshold_3', 1.1),
        'ladder_threshold_4': gate_params.get('ladder_threshold_4', 1.2),
        'ladder_threshold_5': gate_params.get('ladder_threshold_5', 1.3),
        'ladder_threshold_6': gate_params.get('ladder_threshold_6', 1.5),
        'ladder_threshold_7': gate_params.get('ladder_threshold_7', 1.8),
        'ladder_mult_0': gate_params.get('ladder_mult_0', 1),
        'ladder_mult_1': gate_params.get('ladder_mult_1', 2),
        'ladder_mult_2': gate_params.get('ladder_mult_2', 4),
        'ladder_mult_3': gate_params.get('ladder_mult_3', 8),
        'ladder_mult_4': gate_params.get('ladder_mult_4', 16),
        'ladder_mult_5': gate_params.get('ladder_mult_5', 32),
        'ladder_mult_6': gate_params.get('ladder_mult_6', 64),
        'ladder_mult_7': gate_params.get('ladder_mult_7', 128),
        'coef_min': gate_params.get('coef_min', 1.0),
        'coef_max': gate_params.get('coef_max', 2.0),
        'tp_min': gate_params.get('tp_min', 0.005),
        'tp_max': gate_params.get('tp_max', 0.02),
        'rsi_period': gate_params.get('rsi_period', 14),
        'atr_period': gate_params.get('atr_period', 14),
        'compounding_ratio': gate_params.get('compounding_ratio', 0.3),
        'market': gate_params.get('market', 'UNKNOWN'),
        'interval': gate_params.get('interval', '1d'),
        'direction': gate_params.get('direction', 'short'),
    })

    # 运行
    results = cerebro.run()
    strat = results[0]

    # 统计
    start_value = strat.broker_start_value if strat.broker_start_value else cash
    end_value = cerebro.broker.getvalue()
    profit = end_value - start_value
    roi = profit / start_value if start_value != 0 else 0

    # 分析器结果
    sharpe = None
    try:
        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio')
    except:
        pass

    maxdd = 0
    try:
        maxdd = strat.analyzers.dd.get_analysis().get('max', {}).get('drawdown', 0)
    except:
        pass

    sqn = None
    try:
        sqn = strat.analyzers.sqn.get_analysis().get('sqn')
    except:
        pass

    # 交易统计
    trade_count = strat.trade_count
    win_count = strat.win_count
    loss_count = strat.loss_count
    win_rate = win_count / trade_count if trade_count > 0 else 0

    trade_pnls = strat.trade_pnls
    total_pnl = sum(trade_pnls)
    gross_profit = sum(p for p in trade_pnls if p > 0)
    gross_loss = abs(sum(p for p in trade_pnls if p < 0)) if trade_pnls else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    result = {
        'market': gate_params.get('market', 'UNKNOWN'),
        'interval': gate_params.get('interval', 'UNKNOWN'),
        'leverage': leverage,
        'initial_cash': start_value,
        'final_value': end_value,
        'profit': profit,
        'roi': roi,
        'roi_pct': roi * 100,
        'sharpe': sharpe,
        'max_drawdown': maxdd,
        'sqn': sqn,
        'total_trades': trade_count,
        'win_count': win_count,
        'loss_count': loss_count,
        'win_rate': win_rate,
        'win_rate_pct': win_rate * 100,
        'total_pnl': total_pnl,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'profit_factor': profit_factor,
        'equity_curve': strat.get_equity_curve(),
    }

    if verbose:
        print("\n" + "=" * 50)
        print("           BACKTEST SUMMARY")
        print("=" * 50)
        print(f"Market:           {result['market']:>15}")
        print(f"Interval:         {result['interval']:>15}")
        print(f"Leverage:              {result['leverage']:>8}x")
        print("-" * 50)
        print(f"Initial Cash:      {result['initial_cash']:>12.2f}")
        print(f"Final Value:       {result['final_value']:>12.2f}")
        print(f"Profit:            {result['profit']:>12.2f}")
        print(f"ROI:               {result['roi_pct']:>12.2f}%")
        print("-" * 50)
        print(f"Sharpe Ratio:      {str(sharpe):>12}")
        print(f"Max DrawDown:      {maxdd:>12.2f}%")
        print(f"SQN:               {str(sqn):>12}")
        print("-" * 50)
        print(f"Total Trades:      {trade_count:>12}")
        print(f"Win / Loss:        {win_count} / {loss_count}")
        print(f"Win Rate:          {win_rate * 100:>12.2f}%")
        print(f"Profit Factor:     {profit_factor:>12.2f}")
        print("=" * 50)

    return result


# ==================== 参数加载 ====================

def load_gate_params(params_path: str = None, **overrides) -> dict:
    """加载参数"""
    params = {
        'settle': 'usdt',
        'market': 'ETH_USDT',
        'interval': '1d',
        'direction': 'short',
        'leverage': 50,
        'investment': 200,
        'commission': 0.0002,
        'take_profit': 0.25,
        'stop_loss': 0.25,
        'ladder_threshold_0': 0.0,
        'ladder_threshold_1': 0.7,
        'ladder_threshold_2': 0.9,
        'ladder_threshold_3': 1.1,
        'ladder_threshold_4': 1.2,
        'ladder_threshold_5': 1.3,
        'ladder_threshold_6': 1.5,
        'ladder_threshold_7': 1.8,
        'ladder_mult_0': 1,
        'ladder_mult_1': 2,
        'ladder_mult_2': 4,
        'ladder_mult_3': 8,
        'ladder_mult_4': 16,
        'ladder_mult_5': 32,
        'ladder_mult_6': 64,
        'ladder_mult_7': 128,
        'coef_min': 1.0,
        'coef_max': 2.0,
        'tp_min': 0.005,
        'tp_max': 0.02,
        'rsi_period': 14,
        'atr_period': 14,
        'compounding_ratio': 0.3,
    }

    if params_path and os.path.exists(params_path):
        try:
            with open(params_path, 'r') as f:
                params.update(json.load(f))
        except Exception as e:
            print(f"[WARN] Failed to load params: {e}")

    params.update(overrides)
    return params


def export_results(result: dict, export_dir: str = 'results'):
    """导出结果"""
    os.makedirs(export_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_path = os.path.join(export_dir, timestamp)
    os.makedirs(export_path, exist_ok=True)

    equity = result.get('equity_curve', [])
    if equity:
        pd.DataFrame(equity).to_csv(os.path.join(export_path, 'equity.csv'), index=False)
        print(f"[INFO] Equity saved: {export_path}/equity.csv")

    summary = {k: v for k, v in result.items() if k != 'equity_curve'}
    with open(os.path.join(export_path, 'result.json'), 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"[INFO] Result saved: {export_path}/result.json")


def export_html_report(result: dict, export_dir: str = 'results'):
    """
    导出 HTML 友好的结构化数据报告
    
    生成 report.json，包含所有可视化所需的数据结构
    """
    os.makedirs(export_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_path = os.path.join(export_dir, timestamp)
    os.makedirs(export_path, exist_ok=True)

    # 提取权益曲线数据
    equity_curve = result.get('equity_curve', [])
    
    # 计算日收益率序列
    daily_returns = []
    cumulative_returns = []
    dates = []
    
    for i in range(1, len(equity_curve)):
        prev_fund = equity_curve[i-1].get('fund', 0)
        curr_fund = equity_curve[i].get('fund', 0)
        if prev_fund > 0:
            daily_ret = (curr_fund - prev_fund) / prev_fund * 100
            daily_returns.append(round(daily_ret, 4))
        
        initial_fund = equity_curve[0].get('fund', 1)
        if initial_fund > 0:
            cum_ret = (curr_fund - initial_fund) / initial_fund * 100
            cumulative_returns.append(round(cum_ret, 4))
        
        dates.append(equity_curve[i].get('time', ''))

    # 构建 HTML 友好的报告结构
    report = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'version': '1.0',
            'source': 'gate-backtest',
        },
        'backtest_params': {
            'market': result.get('market', 'UNKNOWN'),
            'interval': result.get('interval', '1d'),
            'leverage': result.get('leverage', 50),
            'initial_cash': result.get('initial_cash', 0),
        },
        'key_metrics': {
            'total_return_pct': round(result.get('roi_pct', 0), 2),
            'sharpe_ratio': round(result.get('sharpe', 0), 2) if result.get('sharpe') else None,
            'max_drawdown_pct': round(result.get('max_drawdown', 0), 2),
            'win_rate_pct': round(result.get('win_rate_pct', 0), 2),
            'profit_factor': round(result.get('profit_factor', 0), 2),
            'sqn': round(result.get('sqn', 0), 2) if result.get('sqn') else None,
            'total_trades': result.get('total_trades', 0),
            'win_count': result.get('win_count', 0),
            'loss_count': result.get('loss_count', 0),
            'gross_profit': round(result.get('gross_profit', 0), 2),
            'gross_loss': round(result.get('gross_loss', 0), 2),
        },
        'data_series': {
            'equity': [
                {
                    'time': e.get('time', ''),
                    'price': round(e.get('close', 0), 2),
                    'fund': round(e.get('fund', 0), 2),
                    'position_size': e.get('position_size', 0),
                }
                for e in equity_curve
            ],
            'daily_returns': daily_returns,
            'cumulative_returns': cumulative_returns,
            'dates': dates,
        },
        'chart_data': {
            # 价格与权益曲线
            'price_equity': [
                {
                    'date': e.get('time', '')[:10] if e.get('time') else '',
                    'price': round(e.get('close', 0), 2),
                    'equity': round(e.get('fund', 0), 2),
                }
                for e in equity_curve
            ],
            # 日收益分布
            'return_distribution': _compute_distribution(daily_returns) if daily_returns else [],
        },
    }

    # 保存 JSON
    report_path = os.path.join(export_path, 'report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"[INFO] HTML report data saved: {report_path}")
    
    return report


def _compute_distribution(values: list, bins: int = 20) -> list:
    """计算直方图分布"""
    if not values:
        return []
    
    min_val = min(values)
    max_val = max(values)
    if min_val == max_val:
        return [{'range': f'{min_val:.2f}', 'count': len(values)}]
    
    bin_size = (max_val - min_val) / bins
    distribution = []
    
    for i in range(bins):
        start = min_val + i * bin_size
        end = start + bin_size
        count = sum(1 for v in values if start <= v < end)
        if i == bins - 1:  # 最后一个 bin 包含边界
            count = sum(1 for v in values if start <= v <= end)
        distribution.append({
            'range': f'{start:.2f}~{end:.2f}%',
            'count': count,
            'center': round((start + end) / 2, 2),
        })
    
    return distribution


# ==================== 主入口 ====================

def main():
    parser = argparse.ArgumentParser(description='Backtrader 回测入口')

    # 数据源 (二选一)
    parser.add_argument('--csv', help='本地CSV/GZ文件路径')
    parser.add_argument('--symbol', help='交易对 (CCXT格式: BTC/USDT)')
    parser.add_argument('--exchange', default='gateio', help='交易所 (默认: gateio)')
    parser.add_argument('--interval', default='1m', help='时间间隔 (默认: 1m)')
    parser.add_argument('--hours', type=int, default=24, help='获取多少小时数据 (默认: 24)')

    # 回测参数
    parser.add_argument('--params', help='参数JSON文件')
    parser.add_argument('--cash', type=float, default=10000.0, help='初始资金')
    parser.add_argument('--leverage', type=int, default=50, help='杠杆倍数')
    parser.add_argument('--commission', type=float, default=0.0002, help='手续费率')

    # 秒级优化参数
    parser.add_argument('--second_mode', action='store_true', help='秒级数据模式 (自动调整参数)')

    # 日期过滤 (仅对本地文件有效)
    parser.add_argument('--from', dest='date_from', help='起始日期 (YYYY-MM-DD)')
    parser.add_argument('--to', dest='date_to', help='结束日期 (YYYY-MM-DD)')

    # 导出
    parser.add_argument('--export_dir', default='results', help='导出目录')
    parser.add_argument('--export_html', action='store_true', help='导出 HTML 友好的结构化数据')
    parser.add_argument('--no_export', action='store_true', help='不导出')

    args = parser.parse_args()

    # 检查数据源
    if not args.csv and not args.symbol:
        parser.error("必须指定 --csv 或 --symbol")

    # 加载数据
    if args.csv:
        print(f"[INFO] 加载本地文件: {args.csv}")
        df = load_local_data(args.csv)
        df = filter_by_date(df, args.date_from, args.date_to)
        gate_params = load_gate_params(
            args.params if os.path.exists(args.params) else None,
            leverage=args.leverage,
        )
        gate_params['market'] = os.path.basename(args.csv).split('.')[0]
    else:
        print(f"[INFO] 从 {args.exchange} 获取 {args.symbol} {args.interval} 数据")
        df = load_ccxt_data(
            symbol=args.symbol,
            exchange=args.exchange,
            interval=args.interval,
            hours=args.hours,
        )
        params_file = args.params if args.params and os.path.exists(args.params) else None
        gate_params = load_gate_params(params_file, leverage=args.leverage)
        gate_params['market'] = args.symbol.replace('/', '_')
        gate_params['interval'] = args.interval

        # 秒级模式: 调整参数
        if args.second_mode or args.interval in ('1s', '3s', '5s', '10s'):
            print("[INFO] 秒级模式: 调整策略参数")
            gate_params.update({
                'take_profit': 0.001,
                'stop_loss': 0.001,
                'ladder_threshold_0': 0.0,
                'ladder_threshold_1': 0.02,
                'ladder_threshold_2': 0.04,
                'ladder_threshold_3': 0.06,
                'ladder_threshold_4': 0.08,
                'ladder_threshold_5': 0.10,
                'ladder_threshold_6': 0.12,
                'ladder_threshold_7': 0.14,
                'tp_min': 0.0005,
                'tp_max': 0.001,
                'coef_min': 0.3,
                'coef_max': 0.8,
                'rsi_period': 7,
                'atr_period': 7,
            })

    print(f"[INFO] 数据量: {len(df)} 条")
    print(f"[INFO] 时间范围: {df['datetime'].iloc[0]} ~ {df['datetime'].iloc[-1]}")

    # 运行回测
    result = run_backtest(
        df=df,
        gate_params=gate_params,
        cash=args.cash,
        commission=args.commission,
        leverage=args.leverage,
        verbose=True,
    )

    # 导出
    if not args.no_export:
        export_results(result, args.export_dir)
        if args.export_html:
            export_html_report(result, args.export_dir)


if __name__ == '__main__':
    main()
