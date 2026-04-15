#!/usr/bin/env python3
"""
回测入口脚本
============
使用 Backtrader 适配器运行马丁格尔策略回测

使用方法:
    python examples/backtest_main.py --from 2025-01-01 --to 2026-04-15
    python examples/backtest_main.py --from 2025-06-01 --to 2025-12-31 --leverage 50
"""

import os
import sys
import json
import argparse
from datetime import datetime

import pandas as pd
import numpy as np
import requests

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runner.backtest import BacktestEngine
from runner.strategies import UserStrategy


def std_symbol_binance(market: str) -> str:
    """转换市场符号为 Binance 格式"""
    return market.replace('_', '').upper()


def to_utc_ts(date_str: str) -> int:
    """转换日期字符串为 UTC 时间戳(毫秒)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return int(dt.timestamp() * 1000)


def fetch_klines_gate(symbol: str, interval: str, start_ms: int = None, end_ms: int = None) -> pd.DataFrame:
    """从 Gate.io 获取 K线数据"""
    url = f"https://api.gateio.ws/api/v4/futures/usdt/candlesticks"
    params = {"contract": symbol, "interval": interval}
    if start_ms:
        params["from"] = start_ms // 1000
    if end_ms:
        params["to"] = end_ms // 1000

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=['time', 'volume', 'close', 'high', 'low', 'open'])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['time'] = pd.to_datetime(df['time'].astype(int), unit='s')
        return df.sort_values('time').reset_index(drop=True)
    except Exception as e:
        print(f"[ERROR] Failed to fetch Gate data: {e}")
        return pd.DataFrame()


def fetch_klines_binance(symbol: str, interval: str, start_ms: int = None, end_ms: int = None) -> pd.DataFrame:
    """从 Binance 获取 K线数据"""
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": 1000}
    if start_ms:
        params["startTime"] = start_ms
    if end_ms:
        params["endTime"] = end_ms

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume',
            '_', '_', '_', '_', '_', '_'
        ])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['time'] = pd.to_datetime(df['time'].astype(int), unit='ms')
        return df[['time', 'open', 'high', 'low', 'close', 'volume']].sort_values('time').reset_index(drop=True)
    except Exception as e:
        print(f"[ERROR] Failed to fetch Binance data: {e}")
        return pd.DataFrame()


def load_local_data(symbol: str, interval: str, data_dir: str = 'data') -> pd.DataFrame:
    """尝试从本地加载 Gate.io 历史数据"""
    import glob

    # 标准化 symbol 格式
    symbol = symbol.upper().strip()
    if not symbol.endswith('_USDT'):
        if 'USDT' in symbol:
            symbol = symbol.replace('USDT', '_USDT')
        else:
            symbol = symbol + '_USDT'

    # Gate.io 历史数据目录结构: futures_usdt/candlesticks_1d/YYYYMM/SYMBOL-YYYYMM.csv.gz
    base_dir = f"{data_dir}/gate_history/futures_usdt"

    # 根据时间筛选（如果有的话）
    interval_map = {
        '1m': 'candlesticks_1m',
        '5m': 'candlesticks_5m',
        '15m': 'candlesticks_15m',
        '1h': 'candlesticks_1h',
        '4h': 'candlesticks_4h',
        '1d': 'candlesticks_1d',
    }
    interval_dir = interval_map.get(interval, 'candlesticks_1d')

    # 查找匹配的 gz 文件
    pattern = f"{base_dir}/{interval_dir}/*/{symbol}*.csv.gz"
    files = glob.glob(pattern)

    if not files:
        return pd.DataFrame()

    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, compression='gzip', header=None)
            # Gate.io 格式: timestamp, volume, open, high, low, close
            df.columns = ['timestamp', 'volume', 'open', 'high', 'low', 'close']
            df['time'] = pd.to_datetime(df['timestamp'], unit='s')
            dfs.append(df[['time', 'open', 'high', 'low', 'close', 'volume']])
        except Exception as e:
            print(f"[WARN] Failed to load {f}: {e}")

    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        combined = combined.sort_values('time').reset_index(drop=True)
        combined = combined.drop_duplicates(subset=['time'], keep='first')
        print(f"[INFO] Loaded {len(combined)} candles from {len(files)} files")
        return combined

    return pd.DataFrame()


def load_params(path: str) -> dict:
    """加载参数文件"""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return {}


def parse_args():
    parser = argparse.ArgumentParser(description='Backtest Engine')
    parser.add_argument('--params', type=str, default='configs/params.json', help='参数文件')
    parser.add_argument('--market', type=str, default='ETHUSDT', help='交易对')
    parser.add_argument('--interval', type=str, default='1d', help='K线周期')
    parser.add_argument('--from', dest='date_from', type=str, default='2025-01-01')
    parser.add_argument('--to', dest='date_to', type=str, default='2026-04-15')
    parser.add_argument('--investment', type=float, default=None)
    parser.add_argument('--leverage', type=int, default=None)
    parser.add_argument('--export_dir', type=str, default='results')
    return parser.parse_args()


def main():
    args = parse_args()
    params = load_params(args.params)

    # 命令行参数覆盖
    if args.market:
        params['market'] = args.market
    if args.interval:
        params['interval'] = args.interval
    if args.investment is not None:
        params['investment'] = args.investment
    if args.leverage is not None:
        params['leverage'] = args.leverage
    if args.date_from:
        params['backtest_from'] = args.date_from
    if args.date_to:
        params['backtest_to'] = args.date_to

    # 参数
    investment = params.get('investment', 200)
    leverage = params.get('leverage', 50)
    commission = params.get('commission', 0.0002)

    # 时间转换
    start_ms = to_utc_ts(params.get('backtest_from')) if params.get('backtest_from') else None
    end_ms = to_utc_ts(params.get('backtest_to')) if params.get('backtest_to') else None

    interval = params.get('interval', '1d')
    market = params.get('market', 'ETH_USDT')  # Gate 格式

    # 获取数据
    print(f'[INFO] Fetching data: {market} {interval}')
    print(f'[INFO] Period: {params.get("backtest_from")} ~ {params.get("backtest_to")}')

    # 优先从本地加载
    df = load_local_data(market, interval)

    # 如果本地没有，尝试 Gate.io API
    if df.empty:
        print('[INFO] No local data, trying Gate.io API...')
        df = fetch_klines_gate(market, interval, start_ms, end_ms)

    if df is None or df.empty:
        print('[ERROR] No data fetched. Please check:')
        print('  1. Download data to data/ folder')
        print('  2. Check network connection')
        print('  3. Verify market symbol format (use ETH_USDT for Gate)')
        return

    print(f'[INFO] Got {len(df)} candles')

    # 创建回测引擎
    engine = BacktestEngine(
        cash=investment,
        commission=commission,
        leverage=leverage,
    )

    # 设置数据和策略
    engine.set_data(df)
    engine.set_strategy(
        UserStrategy,
        # 止盈止损
        take_profit=params.get('take_profit', 0.25),
        stop_loss=params.get('stop_loss', 0.25),
        # 马丁格尔参数
        ladder_threshold_0=0.0,
        ladder_threshold_1=params.get('ladder_threshold_1', 0.7),
        ladder_threshold_2=params.get('ladder_threshold_2', 0.9),
        ladder_threshold_3=params.get('ladder_threshold_3', 1.1),
        ladder_threshold_4=params.get('ladder_threshold_4', 1.2),
        ladder_threshold_5=params.get('ladder_threshold_5', 1.3),
        ladder_threshold_6=params.get('ladder_threshold_6', 1.5),
        ladder_threshold_7=params.get('ladder_threshold_7', 1.8),
        ladder_mult_0=1,
        ladder_mult_1=params.get('ladder_mult_1', 2),
        ladder_mult_2=params.get('ladder_mult_2', 4),
        ladder_mult_3=params.get('ladder_mult_3', 8),
        ladder_mult_4=params.get('ladder_mult_4', 16),
        ladder_mult_5=params.get('ladder_mult_5', 32),
        ladder_mult_6=params.get('ladder_mult_6', 64),
        ladder_mult_7=params.get('ladder_mult_7', 128),
        # 动态系数
        coef_min=params.get('coef_min', 1.0),
        coef_max=params.get('coef_max', 2.0),
        # 技术指标
        rsi_period=params.get('rsi_period', 14),
        atr_period=params.get('atr_period', 14),
        # 杠杆（引擎已设置，此处供策略内部使用）
        # 注意：杠杆在 Backtrader 引擎层面设置，不是策略参数
    )

    # 运行回测
    print('[INFO] Running backtest...')
    engine.run(verbose=False)

    # 打印结果
    print(engine.summary())

    # 导出结果
    os.makedirs(args.export_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_dir = os.path.join(args.export_dir, timestamp)
    os.makedirs(export_dir, exist_ok=True)

    # 导出权益曲线
    equity = engine.get_equity_curve()
    if equity:
        eq_df = pd.DataFrame(equity)
        eq_path = os.path.join(export_dir, 'equity.csv')
        eq_df.to_csv(eq_path, index=False)
        print(f'[INFO] Equity saved: {eq_path}')

    # 导出结果摘要
    result = engine.get_results()
    result_path = os.path.join(export_dir, 'result.json')
    with open(result_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f'[INFO] Result saved: {result_path}')

    print(f'[INFO] Done!')


if __name__ == '__main__':
    main()
