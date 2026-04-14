#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gate-Backtest 轻量版回测脚本
基于 Gate 官方 AI 提供的示例代码改造

功能：
- 读取 params.json，支持命令行覆盖参数
- 拉取交易所公开 API 的 K 线数据（Binance/Gate）
- 将 K 线逐根回放给 UserStrategy
- 收集交易明细，导出到 CSV
"""

import os
import json
import time
import math
import argparse
import importlib.util
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Callable

import requests
import pandas as pd


# ============================================================
# 配置：支持 Binance 和 Gate 公共 API
# ============================================================

BINANCE_INTERVAL_MAP = {
    '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
    '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '8h': '8h',
    '12h': '12h', '1d': '1d', '2d': '2d', '3d': '3d', '5d': '5d', '1w': '1w'
}

GATE_INTERVAL_MAP = {
    '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
    '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '8h': '8h',
    '12h': '12h', '1d': '1d', '2d': '2d', '3d': '3d', '5d': '5d', '1w': '1w'
}


# ============================================================
# 工具函数
# ============================================================

def load_strategy(path: str):
    """加载用户策略模块"""
    spec = importlib.util.spec_from_file_location("user_strategy", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    
    if not hasattr(mod, 'UserStrategy'):
        raise RuntimeError(f'{path} 中未找到 UserStrategy 类')
    
    return mod.UserStrategy


def parse_args():
    """解析命令行参数"""
    p = argparse.ArgumentParser(description='Gate-Backtest 轻量版回测')
    
    p.add_argument('--strategy', default='strategies/user_strategy.py', help='策略文件路径')
    p.add_argument('--params', default='configs/params.json', help='参数配置文件')
    p.add_argument('--from', dest='date_from', default=None, help='回测开始日期 YYYY-MM-DD')
    p.add_argument('--to', dest='date_to', default=None, help='回测结束日期 YYYY-MM-DD')
    p.add_argument('--market', default=None, help='交易对 (如 ETH_USDT)')
    p.add_argument('--interval', default=None, help='K线周期 (1m, 15m, 1h, 1d...)')
    p.add_argument('--investment', type=float, default=None, help='初始投资金额 USDT')
    p.add_argument('--leverage', type=int, default=None, help='杠杆倍数')
    p.add_argument('--datasource', default='binance', choices=['binance', 'gate'], help='数据源')
    p.add_argument('--export_dir', default='results', help='结果导出目录')
    
    return p.parse_args()


def to_utc_ts(date_str: str) -> int:
    """日期字符串转 UTC 毫秒时间戳"""
    dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def standardize_symbol_for_binance(market: str) -> str:
    """转换交易对格式: ETH_USDT -> ETHUSDT"""
    return market.replace('_', '')


# ============================================================
# 数据获取
# ============================================================

def fetch_klines_binance(symbol: str, interval: str, start: int = None, end: int = None, limit: int = None) -> pd.DataFrame:
    """
    从 Binance U本位合约 API 获取K线数据
    端点: https://fapi.binance.com/fapi/v1/klines
    """
    base = 'https://fapi.binance.com/fapi/v1/klines'
    params = {
        'symbol': symbol.upper(),
        'interval': BINANCE_INTERVAL_MAP.get(interval, '1d'),
    }
    
    if limit:
        params['limit'] = min(limit, 1500)
    if start is not None:
        params['startTime'] = start
    if end is not None:
        params['endTime'] = end
    
    all_rows = []
    cur_start = start
    
    while True:
        q = params.copy()
        if cur_start is not None:
            q['startTime'] = cur_start
        
        resp = requests.get(base, params=q, timeout=30)
        resp.raise_for_status()
        rows = resp.json()
        
        if not rows:
            break
        
        all_rows.extend(rows)
        last_ts = rows[-1][0]
        cur_start = last_ts + 1
        
        if end is not None and last_ts >= end:
            break
        
        time.sleep(0.2)  # 避免频率限制
    
    if not all_rows:
        return pd.DataFrame()
    
    # 解析数据
    df = pd.DataFrame(all_rows, columns=['t', 'o', 'h', 'l', 'c', 'v', 'ct', 'qv', 'n', 'tb', 'tqv', 'ignore'])
    df = df[['t', 'o', 'h', 'l', 'c', 'v']].copy()
    
    for col in ['o', 'h', 'l', 'c', 'v']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df['t'] = pd.to_datetime(df['t'], unit='ms', utc=True)
    df.rename(columns={'t': 'time', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
    
    return df


def fetch_klines_gate(symbol: str, interval: str, start: int = None, end: int = None) -> pd.DataFrame:
    """
    从 Gate.io 合约 API 获取K线数据
    端点: /futures/usdt/candlesticks
    """
    base = 'https://api.gateio.ws/api/v4/futures/usdt/candlesticks'
    
    # Gate 永续合约格式: ETH_USDT
    # 处理各种输入格式: ETH_USDT, ETHUSDT, ETH-USDT
    contract = symbol.replace('-', '_')
    if '_USDT' not in contract and 'USDT' in contract:
        contract = contract.replace('USDT', '_USDT')
    elif 'USDT' not in contract:
        contract = contract + '_USDT'
    
    q = {
        'contract': contract,
        'interval': GATE_INTERVAL_MAP.get(interval, '1d'),
    }
    
    if start is not None:
        q['from'] = int(start / 1000)
    if end is not None:
        q['to'] = int(end / 1000)
    
    print(f"[Gate API] contract={contract}, interval={q['interval']}")
    
    resp = requests.get(base, params=q, timeout=30)
    resp.raise_for_status()
    rows = resp.json()
    
    if not rows:
        print(f"[Gate API] 返回空数据")
        return pd.DataFrame()
    
    print(f"[Gate API] 获取 {len(rows)} 条数据")
    
    # Gate 返回按时间倒序，需要翻转
    rows = rows[::-1]
    
    # 字段顺序: t, v, c, h, l, o
    df = pd.DataFrame(rows, columns=['t', 'v', 'c', 'h', 'l', 'o'])
    
    for col in ['o', 'h', 'l', 'c', 'v']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df['t'] = pd.to_datetime(df['t'], unit='s', utc=True)
    df.rename(columns={'t': 'time', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
    
    return df


def slice_by_time(df: pd.DataFrame, start_ms: int, end_ms: int) -> pd.DataFrame:
    """按时间范围切片"""
    if df.empty:
        return df
    
    m1 = True if start_ms is None else df['time'] >= pd.to_datetime(start_ms, unit='ms', utc=True)
    m2 = True if end_ms is None else df['time'] <= pd.to_datetime(end_ms, unit='ms', utc=True)
    
    if isinstance(m1, bool):
        return df[m2].copy()
    return df[m1 & m2].copy()


# ============================================================
# 简单回测引擎
# ============================================================

class SimpleBroker:
    """简单经纪商模拟"""
    def __init__(self, commission: float = 0.0002):
        self.commission = commission


class Engine:
    """回测引擎 - 驱动 UserStrategy"""
    
    def __init__(self, StrategyCls, params: Dict[str, Any], klines: pd.DataFrame):
        # 初始化策略（无参数）
        self.strategy = StrategyCls()
        
        # 更新策略参数
        if hasattr(self.strategy, '_params'):
            self.strategy._params.update(params)
        elif hasattr(self.strategy, 'params'):
            self.strategy.params.update(params)
        
        # 设置经纪商
        self.strategy.broker = SimpleBroker(commission=params.get('commission', 0.0002))
        self.klines = klines.reset_index(drop=True)
        
        # 缓存数据到策略可访问的形式
        self._setup_strategy_methods()
        
        # 数据收集容器
        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: List[Dict[str, Any]] = []
        self.idx = -1
        self.cur_close = None
    
    def _setup_strategy_methods(self):
        """设置策略的方法适配"""
        
        # 保存方法引用供 next() 使用
        self._sell_func = None
        self._close_func = None
        self._position = None
        
        # get_klines: 获取历史K线（映射到策略期望的列名格式）
        def _get_klines(limit: int = 50, as_df: bool = True):
            if self.idx < 0:
                return None
            start = max(0, self.idx - limit + 1)
            df = self.klines.iloc[start:self.idx + 1].copy()
            
            # 映射列名以匹配策略期望的格式
            df = df.rename(columns={
                'open': 'o',
                'high': 'h', 
                'low': 'l',
                'close': 'c',
                'volume': 'v'
            })
            
            return df if as_df else df.values
        
        self.strategy.get_klines = _get_klines
        
        # position 持仓
        self._position = type('Pos', (), {'size': 0.0})()
        self.strategy.position = self._position
        
        # sell: 开仓
        def _sell(size: float = None):
            if size is None:
                size = 0.0
            self._position.size -= size
            
            class OrderResult:
                status = 'Completed'
                isbuy = lambda self: False
                issell = lambda self: True
                executed = type('E', (), {'price': float(self.cur_close)})()
            
            return OrderResult()
        
        self._sell_func = _sell
        self.strategy.sell = _sell
        
        # close: 平仓
        def _close():
            self._position.size = 0.0
            
            class OrderResult:
                status = 'Completed'
                isbuy = lambda self: True
                issell = lambda self: False
                executed = type('E', (), {'price': float(self.cur_close)})()
            
            return OrderResult()
        
        self._close_func = _close
        self.strategy.close = _close
        
        # notify_order: 订单回调（默认空实现）
        if not hasattr(self.strategy, 'notify_order'):
            self.strategy.notify_order = lambda x: None
    
    def _call_strategy_next(self):
        """调用策略的 next 方法（Gate.io 风格）"""
        self.strategy.next(
            get_klines_func=self.strategy.get_klines,
            sell_func=self._sell_func,
            close_func=self._close_func,
            position=self._position
        )
    
    def run(self):
        """运行回测 - 逐根回放"""
        print(f"[INFO] 开始回测，共 {len(self.klines)} 根K线")
        
        for i in range(len(self.klines)):
            self.idx = i
            self.cur_close = self.klines.loc[i, 'close']
            
            # 记录权益曲线
            self.equity_curve.append({
                'time': self.klines.loc[i, 'time'],
                'close': self.cur_close,
                'position_size': self.strategy.position.size
            })
            
            try:
                self._call_strategy_next()
            except Exception as e:
                print(f"[ERROR] 第 {i} 根K线执行异常: {e}")
                import traceback
                traceback.print_exc()
                break
        
        print('[INFO] 回测结束')


# ============================================================
# 结果导出与统计
# ============================================================

def export_results(export_dir: str, klines: pd.DataFrame, equity: List[Dict]):
    """导出回测结果"""
    os.makedirs(export_dir, exist_ok=True)
    
    # 导出 equity
    if equity:
        eq_df = pd.DataFrame(equity)
        eq_path = os.path.join(export_dir, 'equity.csv')
        eq_df.to_csv(eq_path, index=False)
        print(f"[EXPORT] equity.csv -> {eq_path}")
    
    # 导出 K线数据
    klines_path = os.path.join(export_dir, 'klines.csv')
    klines.to_csv(klines_path, index=False)
    print(f"[EXPORT] klines.csv -> {klines_path}")


def print_summary(params: Dict, equity: List[Dict]):
    """打印回测汇总"""
    print("\n" + "=" * 50)
    print("回测汇总")
    print("=" * 50)
    print(f"市场: {params.get('market', 'N/A')}")
    print(f"周期: {params.get('interval', 'N/A')}")
    print(f"时间: {params.get('backtest_from', 'N/A')} -> {params.get('backtest_to', 'N/A')}")
    print(f"投资额: {params.get('investment', 1000)} USDT")
    print(f"杠杆: {params.get('leverage', 1)}x")
    print(f"数据源: {params.get('datasource', 'binance')}")
    print("=" * 50)


# ============================================================
# 主入口
# ============================================================

def main():
    args = parse_args()
    
    # 加载参数
    if os.path.exists(args.params):
        with open(args.params, 'r', encoding='utf-8') as f:
            params = json.load(f)
    else:
        params = {}
        print(f"[WARN] 参数文件 {args.params} 不存在，使用命令行参数")
    
    # 命令行覆盖参数
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
    if args.datasource:
        params['datasource'] = args.datasource
    
    # 设置默认值
    params.setdefault('market', 'ETH_USDT')
    params.setdefault('interval', '1d')
    params.setdefault('investment', 1000)
    params.setdefault('leverage', 1)
    params.setdefault('commission', 0.0004)
    
    # 时间范围
    start_ms = to_utc_ts(params.get('backtest_from')) if params.get('backtest_from') else None
    end_ms = to_utc_ts(params.get('backtest_to')) if params.get('backtest_to') else None
    
    # 获取K线数据
    interval = params.get('interval', '1d')
    market = params.get('market', 'ETH_USDT')
    
    print(f"[INFO] 数据源: {args.datasource}")
    print(f"[INFO] 获取 {market} {interval} 数据...")
    
    if args.datasource == 'binance':
        sym = standardize_symbol_for_binance(market)
        df = fetch_klines_binance(sym, interval, start_ms, end_ms)
    else:
        df = fetch_klines_gate(market, interval, start_ms, end_ms)
    
    if df is None or df.empty:
        print('[ERROR] 未获取到K线数据，请检查市场、周期与时间范围')
        return
    
    print(f"[INFO] 获取到 {len(df)} 根K线")
    
    # 切片到目标区间
    df = slice_by_time(df, start_ms, end_ms)
    print(f"[INFO] 切片后 {len(df)} 根K线")
    
    # 加载策略
    # 尝试多种路径格式
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', args.strategy),
        os.path.join(os.path.dirname(__file__), '..', 'runner', 'strategies', 'user_strategy.py'),
        args.strategy,
    ]
    
    strategy_path = None
    for p in possible_paths:
        if os.path.exists(p):
            strategy_path = p
            break
    
    if strategy_path is None:
        print(f"[ERROR] 策略文件不存在: {args.strategy}")
        print(f"[ERROR] 尝试过的路径: {possible_paths}")
        return
    
    print(f"[INFO] 加载策略: {strategy_path}")
    
    print(f"[INFO] 加载策略: {strategy_path}")
    StrategyCls = load_strategy(strategy_path)
    
    # 运行回测
    engine = Engine(StrategyCls, params, df)
    engine.run()
    
    # 导出结果
    export_results(args.export_dir, df, engine.equity_curve)
    
    # 打印汇总
    print_summary(params, engine.equity_curve)


if __name__ == '__main__':
    main()
