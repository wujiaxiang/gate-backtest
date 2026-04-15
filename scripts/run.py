#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gate-Backtest 回测主入口

用法:
    python scripts/run.py --config configs/params.json
    python scripts/run.py --market ETH_USDT --interval 1m --from 2025-01-01 --to 2026-04-15

特性:
- 技术指标预计算优化
- 多进程并行回测（按月份）
- 自动生成可视化报告
"""

import os
import sys
import json
import time
import math
import argparse
import importlib.util
import multiprocessing as mp
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from functools import partial

import requests
import pandas as pd
import numpy as np

# ============================================================
# 常量
# ============================================================

BINANCE_INTERVAL_MAP = {
    '1m': '1m', '5m': '5m', '15m': '15m',
    '1h': '1h', '4h': '4h', '1d': '1d', '1w': '1w'
}

GATE_INTERVAL_MAP = {
    '1m': '1m', '5m': '5m', '15m': '15m',
    '1h': '1h', '4h': '4h', '1d': '1d', '1w': '1w'
}


# ============================================================
# 日志重定向
# ============================================================

class TeePrinter:
    """同时输出到终端和日志文件"""
    def __init__(self, log_path: str):
        self.log_path = log_path
        self.log_file = None
    
    def start(self):
        self.log_file = open(self.log_path, 'w', encoding='utf-8')
        self._redirect_stdout()
    
    def _redirect_stdout(self):
        import sys
        class DualOutput:
            def __init__(self, file, original):
                self.file = file
                self.original = original
            def write(self, text):
                self.file.write(text)
                self.original.write(text)
                self.file.flush()
            def flush(self):
                self.file.flush()
                self.original.flush()
        sys.stdout = DualOutput(self.log_file, sys.__stdout__)
    
    def stop(self):
        if self.log_file:
            self.log_file.close()
            self.log_file = None
            import sys
            sys.stdout = sys.__stdout__

@contextmanager
def log_to_file(log_path: str):
    printer = TeePrinter(log_path)
    printer.start()
    try:
        yield printer
    finally:
        printer.stop()


# ============================================================
# 策略加载
# ============================================================

def load_strategy(path: str):
    """加载用户策略模块"""
    spec = importlib.util.spec_from_file_location("user_strategy", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, 'UserStrategy'):
        raise RuntimeError(f'{path} 中未找到 UserStrategy 类')
    return mod.UserStrategy


# ============================================================
# 命令行参数
# ============================================================

def parse_args():
    """解析命令行参数"""
    p = argparse.ArgumentParser(
        description='Gate-Backtest: 高性能量化策略回测框架',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/run.py --config configs/params.json
  python scripts/run.py --market ETH_USDT --interval 1m --from 2025-01-01 --to 2026-04-15
  python scripts/run.py --market ETH_USDT --interval 1d --investment 200 --leverage 50
        """
    )
    
    # 策略配置
    p.add_argument('--strategy', default='runner/strategies/user_strategy.py', 
                   help='策略文件路径 (default: runner/strategies/user_strategy.py)')
    p.add_argument('--params', default='configs/params.json', 
                   help='参数配置文件 (default: configs/params.json)')
    
    # 数据参数
    p.add_argument('--market', '-m', default=None, help='交易对 (如 ETH_USDT)')
    p.add_argument('--interval', '-i', default=None, help='K线周期 (1m, 15m, 1h, 1d...)')
    p.add_argument('--from', dest='date_from', default=None, help='回测开始日期 YYYY-MM-DD')
    p.add_argument('--to', dest='date_to', default=None, help='回测结束日期 YYYY-MM-DD')
    
    # 数据源
    p.add_argument('--datasource', '-d', default='gate_history',
                   choices=['binance', 'gate', 'gate_history'],
                   help='数据源 (default: gate_history)')
    p.add_argument('--biz', default='futures_usdt',
                   choices=['spot', 'futures_usdt', 'futures_btc'],
                   help='Gate历史数据的业务类型')
    p.add_argument('--data-file', default=None,
                   help='使用本地CSV数据文件')
    p.add_argument('--save-data', action='store_true',
                   help='保存获取的数据到本地')
    
    # 策略参数
    p.add_argument('--investment', type=float, default=None, help='初始投资金额 USDT')
    p.add_argument('--leverage', type=int, default=None, help='杠杆倍数')
    
    # 输出配置
    p.add_argument('--export-dir', default='results', help='结果导出目录 (default: results)')
    p.add_argument('--workers', type=int, default=None, 
                   help='并行worker数量 (默认: CPU核心数)')
    p.add_argument('--no-parallel', action='store_true',
                   help='禁用并行回测')
    
    return p.parse_args()


# ============================================================
# 数据获取
# ============================================================

def fetch_klines_binance(symbol: str, interval: str, start: int = None, end: int = None) -> pd.DataFrame:
    """从 Binance U本位合约 API 获取K线数据"""
    base = 'https://fapi.binance.com/fapi/v1/klines'
    params = {'symbol': symbol.upper(), 'interval': BINANCE_INTERVAL_MAP.get(interval, '1d')}
    
    if start is not None: params['startTime'] = start
    if end is not None: params['endTime'] = end
    
    all_rows = []
    cur_start = start
    
    while True:
        q = params.copy()
        if cur_start is not None: q['startTime'] = cur_start
        resp = requests.get(base, params=q, timeout=30)
        resp.raise_for_status()
        rows = resp.json()
        if not rows: break
        all_rows.extend(rows)
        last_ts = rows[-1][0]
        cur_start = last_ts + 1
        if end and last_ts >= end: break
        time.sleep(0.2)
    
    if not all_rows: return pd.DataFrame()
    
    df = pd.DataFrame(all_rows, columns=['t', 'o', 'h', 'l', 'c', 'v', 'ct', 'qv', 'n', 'tb', 'tqv', 'ignore'])
    df = df[['t', 'o', 'h', 'l', 'c', 'v']].copy()
    for col in ['o', 'h', 'l', 'c', 'v']: df[col] = pd.to_numeric(df[col], errors='coerce')
    df['t'] = pd.to_datetime(df['t'], unit='ms', utc=True)
    df.rename(columns={'t': 'time', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
    return df


def fetch_klines_gate(symbol: str, interval: str, start: int = None, end: int = None) -> pd.DataFrame:
    """从 Gate.io 合约 API 获取K线数据"""
    base = 'https://api.gateio.ws/api/v4/futures/usdt/candlesticks'
    contract = symbol.replace('-', '_')
    if '_USDT' not in contract and 'USDT' in contract: contract = contract.replace('USDT', '_USDT')
    elif 'USDT' not in contract: contract = contract + '_USDT'
    
    q = {'contract': contract, 'interval': GATE_INTERVAL_MAP.get(interval, '1d')}
    if start: q['from'] = int(start / 1000)
    if end: q['to'] = int(end / 1000)
    
    resp = requests.get(base, params=q, timeout=30)
    resp.raise_for_status()
    rows = resp.json()
    if not rows: return pd.DataFrame()
    
    rows = rows[::-1]
    df = pd.DataFrame(rows, columns=['t', 'v', 'c', 'h', 'l', 'o'])
    for col in ['o', 'h', 'l', 'c', 'v']: df[col] = pd.to_numeric(df[col], errors='coerce')
    df['t'] = pd.to_datetime(df['t'].astype(int), unit='s', utc=True)
    df.rename(columns={'t': 'time', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
    return df


def fetch_klines_gate_history(market: str, interval: str, start_date: str, end_date: str, 
                               biz: str = 'futures_usdt', data_dir: str = 'data/gate_history') -> pd.DataFrame:
    """从 Gate 历史批量数据下载"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from runner.data.gate_histor import GateHistoricalDownloader
    
    downloader = GateHistoricalDownloader(biz=biz, data_dir=data_dir)
    df = downloader.download_ohlcv(
        market=market, interval=interval,
        start_date=start_date, end_date=end_date, verbose=True
    )
    
    if df is None or df.empty: return pd.DataFrame()
    df = df.rename(columns={'timestamp': 'time', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
    return df


def load_klines_from_csv(file_path: str) -> pd.DataFrame:
    """从本地CSV加载K线数据"""
    df = pd.read_csv(file_path)
    if 'time' not in df.columns and 'timestamp' in df.columns:
        df.rename(columns={'timestamp': 'time'}, inplace=True)
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], utc=True)
    return df


def to_utc_ts(date_str: str) -> int:
    """日期字符串转 UTC 毫秒时间戳"""
    dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def slice_by_time(df: pd.DataFrame, start_ms: int = None, end_ms: int = None) -> pd.DataFrame:
    """按时间范围切片"""
    if df.empty: return df
    m1 = True if start_ms is None else df['time'] >= pd.to_datetime(start_ms, unit='ms', utc=True)
    m2 = True if end_ms is None else df['time'] <= pd.to_datetime(end_ms, unit='ms', utc=True)
    if isinstance(m1, bool): return df[m2].copy()
    return df[m1 & m2].copy()


# ============================================================
# 简单回测引擎（带预计算优化）
# ============================================================

class SimpleBroker:
    def __init__(self, commission: float = 0.0002):
        self.commission = commission


class Engine:
    """回测引擎 - 支持预计算优化"""
    
    def __init__(self, StrategyCls, params: Dict[str, Any], klines: pd.DataFrame):
        self.strategy = StrategyCls()
        
        # 更新策略参数
        if hasattr(self.strategy, '_params'):
            self.strategy._params.update(params)
        elif hasattr(self.strategy, 'params'):
            self.strategy.params.update(params)
        
        self.strategy.broker = SimpleBroker(commission=params.get('commission', 0.0002))
        self.klines = klines.reset_index(drop=True)
        
        # 预计算技术指标
        self._precomputed = {}
        self._precompute_indicators(params)
        self._setup_strategy_methods()
        
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.idx = -1
        self.cur_close = None
    
    def _precompute_indicators(self, params: Dict[str, Any]):
        """预计算所有技术指标"""
        try:
            import talib
            rsi_period = int(params.get('rsi_period', 14))
            atr_period = int(params.get('atr_period', 14))
            
            if len(self.klines) < max(rsi_period, atr_period) + 5: return
            
            print(f"[INFO] 预计算指标: RSI({rsi_period}), ATR({atr_period})...")
            
            close = pd.to_numeric(self.klines['close'], errors='coerce').values
            high = pd.to_numeric(self.klines.get('high', close), errors='coerce').values
            low = pd.to_numeric(self.klines.get('low', close), errors='coerce').values
            
            rsi = talib.RSI(close.astype(np.float64), timeperiod=rsi_period)
            atr = talib.ATR(high.astype(np.float64), low.astype(np.float64), close.astype(np.float64), timeperiod=atr_period)
            
            self._precomputed = {
                'rsi': rsi, 'rsi_period': rsi_period,
                'atr': atr, 'atr_period': atr_period,
                'close': close, 'high': high, 'low': low,
            }
            print(f"[INFO] 预计算完成，共 {len(self.klines)} 条数据")
        except ImportError:
            print("[WARN] talib 未安装，跳过预计算")
    
    def _create_talib_proxy(self):
        """创建talib代理"""
        try:
            import talib
        except ImportError:
            return None
        
        precomp = self._precomputed
        rsi_p, atr_p = precomp.get('rsi_period', 14), precomp.get('atr_period', 14)
        
        def proxy_rsi(close, timeperiod=14):
            if timeperiod == rsi_p and len(precomp['close']) == len(close):
                return precomp['rsi']
            return talib.RSI(close, timeperiod)
        
        def proxy_atr(high, low, close, timeperiod=14):
            if timeperiod == atr_p:
                if len(close) == len(precomp['close']) == len(precomp['high']) == len(precomp['low']):
                    return precomp['atr']
            return talib.ATR(high, low, close, timeperiod)
        
        class TalibProxy:
            RSI = staticmethod(proxy_rsi)
            ATR = staticmethod(proxy_atr)
            def __getattr__(self, name):
                return getattr(talib, name)
        return TalibProxy()
    
    def _setup_strategy_methods(self):
        self._sell_func = None
        self._close_func = None
        self._position = type('Pos', (), {'size': 0.0})()
        self.strategy.position = self._position
        
        # 注入talib代理
        if self._precomputed:
            self.strategy.talib = self._create_talib_proxy()
        
        # get_klines
        def _get_klines(limit: int = 50, as_df: bool = True):
            if self.idx < 0: return None
            start = max(0, self.idx - limit + 1)
            df = self.klines.iloc[start:self.idx + 1].copy()
            df = df.rename(columns={'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c', 'volume': 'v'})
            return df if as_df else df.values
        self.strategy.get_klines = _get_klines
        
        # sell
        def _sell(size: float = None):
            if size is None or size == 0.0:
                size = getattr(self.strategy, 'base_quantity', 0.0) or 0.0
            self._position.size -= size
            class OrderResult:
                status = 'Completed'
                isbuy = property(lambda self: False)
                issell = property(lambda self: True)
                executed = type('E', (), {'price': float(self.cur_close)})()
            return OrderResult()
        self._sell_func = _sell
        self.strategy.sell = _sell
        
        # close
        def _close():
            self._position.size = 0.0
            class OrderResult:
                status = 'Completed'
                isbuy = property(lambda self: True)
                issell = property(lambda self: False)
                executed = type('E', (), {'price': float(self.cur_close)})()
            return OrderResult()
        self._close_func = _close
        self.strategy.close = _close
        
        if not hasattr(self.strategy, 'notify_order'):
            self.strategy.notify_order = lambda x: None
    
    def _call_strategy_next(self):
        self.strategy.next(
            get_klines_func=self.strategy.get_klines,
            sell_func=self._sell_func,
            close_func=self._close_func,
            position=self.strategy.position
        )
    
    def run(self, verbose: bool = True) -> 'Engine':
        """运行回测"""
        total = len(self.klines)
        if verbose:
            print(f"[INFO] 开始回测，共 {total:,} 根K线")
        
        log_threshold = max(1, total // 20)
        last_log_pct = 0
        
        for i in range(total):
            self.idx = i
            self.cur_close = self.klines.loc[i, 'close']
            self.strategy.order = None
            
            self.equity_curve.append({
                'time': self.klines.loc[i, 'time'],
                'close': self.cur_close,
                'position_size': self.strategy.position.size,
                'fund': getattr(self.strategy, 'current_investment', 
                              self.strategy._params.get('investment', 200) if hasattr(self.strategy, '_params') else 200)
            })
            
            try:
                self._call_strategy_next()
            except Exception as e:
                print(f"[ERROR] 第 {i} 根K线执行异常: {e}")
                import traceback; traceback.print_exc()
                break
            
            if verbose and (i + 1) % min(log_threshold, 10000) == 0:
                pct = (i + 1) / total * 100
                if pct >= last_log_pct + 5:
                    cur_time = self.klines.loc[i, 'time']
                    print(f"[PROGRESS] {pct:5.1f}% | {cur_time} | {self.cur_close:>10.2f}")
                    last_log_pct = pct
        
        if verbose: print('[INFO] 回测结束')
        return self


# ============================================================
# 并行回测
# ============================================================

def _run_month_backtest(args_tuple) -> Dict[str, Any]:
    """单月回测（供多进程调用）"""
    month_str, klines_data, params, strategy_path = args_tuple
    
    # 重新加载策略（避免 pickle 问题）
    StrategyCls = load_strategy(strategy_path)
    
    # 重建DataFrame
    df = pd.DataFrame(klines_data)
    df['time'] = pd.to_datetime(df['time'], utc=True)
    
    # 运行回测
    engine = Engine(StrategyCls, params, df)
    engine.run(verbose=False)
    
    return {
        'month': month_str,
        'equity_curve': engine.equity_curve,
        'trades': engine.trades,
        'count': len(engine.equity_curve)
    }


def run_parallel(klines: pd.DataFrame, StrategyCls, params: Dict[str, Any], 
                 workers: int = None, strategy_path: str = None) -> Dict[str, Any]:
    """按月份并行回测"""
    if workers is None:
        workers = max(1, mp.cpu_count() - 1)
    
    print(f"[INFO] 启动 {workers} 个并行进程...")
    
    # 按月份分割数据
    klines = klines.copy()
    klines['month'] = klines['time'].dt.to_period('M')
    months = klines['month'].unique()
    print(f"[INFO] 数据跨度: {len(months)} 个月")
    
    # 保存策略路径（用于子进程重新加载）
    if strategy_path is None:
        strategy_path = 'runner/strategies/user_strategy.py'
    
    # 准备每个月的K线数据（转为基础类型以支持pickle）
    klines_data_list = []
    for m in sorted(months):
        month_klines = klines[klines['month'] == m].copy()
        data_dict = month_klines.to_dict('list')
        for col in data_dict:
            data_dict[col] = [float(x) if isinstance(x, (np.floating, np.integer)) else x 
                             for x in data_dict[col]]
        klines_data_list.append((str(m), data_dict))
    
    # 并行执行
    with mp.Pool(processes=workers) as pool:
        results = pool.map(_run_month_backtest, 
                          [(m, d, params, strategy_path) for m, d in klines_data_list])
    
    # 合并结果
    combined_equity = []
    for r in sorted(results, key=lambda x: x['month']):
        combined_equity.extend(r['equity_curve'])
    
    print(f"[INFO] 并行回测完成，共 {len(combined_equity)} 条记录")
    
    return {
        'equity_curve': combined_equity,
        'trades': [],
        'months_processed': len(results)
    }


# ============================================================
# 结果导出
# ============================================================

def export_results(dated_dir: str, klines: pd.DataFrame, equity: List[Dict], params: Dict = None):
    """导出回测结果"""
    print(f"[INFO] 结果目录: {dated_dir}")
    
    # 导出 equity
    if equity:
        eq_df = pd.DataFrame(equity)
        eq_path = os.path.join(dated_dir, 'equity.csv')
        eq_df.to_csv(eq_path, index=False)
        print(f"[EXPORT] equity.csv -> {eq_path}")
        
        # 按天汇总
        eq_df['time'] = pd.to_datetime(eq_df['time'])
        eq_df['date'] = eq_df['time'].dt.date
        
        daily_equity = eq_df.groupby('date').agg({
            'close': 'last',
            'position_size': 'last',
            'fund': 'last'
        }).reset_index()
        daily_equity['daily_return'] = daily_equity['fund'].pct_change()
        base_fund = daily_equity['fund'].iloc[0]
        daily_equity['cum_return'] = (daily_equity['fund'] / base_fund - 1) * 100
        
        daily_path = os.path.join(dated_dir, 'daily_equity.csv')
        daily_equity.to_csv(daily_path, index=False)
        print(f"[EXPORT] daily_equity.csv -> {daily_path}")
    
    # 导出 K线
    klines_path = os.path.join(dated_dir, 'klines.csv')
    klines.to_csv(klines_path, index=False)
    print(f"[EXPORT] klines.csv -> {klines_path}")
    
    # 生成JSON结果
    if params:
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from export_results import load_equity_data, load_klines_data, generate_json_result, save_json_result
            
            eq_df = load_equity_data(eq_path)
            kl_df = load_klines_data(klines_path)
            json_result = generate_json_result(eq_df, kl_df, params)
            
            json_path = os.path.join(dated_dir, 'backtest_result.json')
            save_json_result(json_result, json_path)
            print(f"[EXPORT] backtest_result.json -> {json_path}")
            
            # 提示HTML报告
            html_path = os.path.join(os.path.dirname(dated_dir), 'html', 'backtest_report.html')
            print(f"\n[INFO] HTML可视化报告: open {html_path}")
            print(f"[INFO] 选择 {json_path} 查看")
        except Exception as e:
            print(f"[WARN] 生成JSON结果失败: {e}")


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
        print(f"[WARN] 参数文件 {args.params} 不存在")
    
    # 命令行覆盖参数
    if args.market: params['market'] = args.market
    if args.interval: params['interval'] = args.interval
    if args.date_from: params['backtest_from'] = args.date_from
    if args.date_to: params['backtest_to'] = args.date_to
    if args.investment is not None: params['investment'] = args.investment
    if args.leverage is not None: params['leverage'] = args.leverage
    
    # 默认参数
    params.setdefault('market', 'ETH_USDT')
    params.setdefault('interval', '1d')
    params.setdefault('backtest_from', '2025-01-01')
    params.setdefault('backtest_to', '2026-04-15')
    params.setdefault('investment', 200)
    params.setdefault('leverage', 50)
    params.setdefault('commission', 0.0004)
    
    # 日志管理
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    logs_dir = os.path.join(project_root, 'logs')
    latest_log = os.path.join(logs_dir, 'backtest_latest.log')
    os.makedirs(logs_dir, exist_ok=True)
    
    # 备份上次日志
    if os.path.exists(latest_log):
        import shutil
        backup_name = f'backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        backup_path = os.path.join(args.export_dir, backup_name)
        try:
            shutil.copy(latest_log, backup_path)
            print(f"[INFO] 上次日志已备份: {backup_name}")
        except Exception: pass
    
    # 创建结果目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dated_dir = os.path.join(args.export_dir, timestamp)
    os.makedirs(dated_dir, exist_ok=True)
    log_path = latest_log
    
    print("=" * 60)
    print("Gate-Backtest 回测框架")
    print("=" * 60)
    print(f"市场: {params['market']}")
    print(f"周期: {params['interval']}")
    print(f"时间: {params['backtest_from']} -> {params['backtest_to']}")
    print(f"投资额: {params['investment']} USDT")
    print(f"杠杆: {params['leverage']}x")
    print(f"数据源: {args.datasource}")
    print("=" * 60)
    
    with log_to_file(log_path):
        print("[INFO] 日志文件:", log_path)
        
        # 获取K线数据
        print(f"[INFO] 获取数据...")
        
        if args.data_file and os.path.exists(args.data_file):
            print(f"[INFO] 从本地文件加载: {args.data_file}")
            df = load_klines_from_csv(args.data_file)
        elif args.datasource == 'binance':
            sym = params['market'].replace('_', '')
            df = fetch_klines_binance(
                sym, params['interval'],
                to_utc_ts(params['backtest_from']),
                to_utc_ts(params['backtest_to'])
            )
        elif args.datasource == 'gate':
            df = fetch_klines_gate(
                params['market'], params['interval'],
                to_utc_ts(params['backtest_from']),
                to_utc_ts(params['backtest_to'])
            )
        else:  # gate_history
            df = fetch_klines_gate_history(
                market=params['market'],
                interval=params['interval'],
                start_date=params['backtest_from'],
                end_date=params['backtest_to'],
                biz=args.biz,
                data_dir='data/gate_history'
            )
        
        if df is None or df.empty:
            print("[ERROR] 数据获取失败")
            return
        
        print(f"[INFO] 获取 {len(df):,} 条K线")
        
        # 切片到指定范围
        start_ms = to_utc_ts(params['backtest_from']) if params.get('backtest_from') else None
        end_ms = to_utc_ts(params['backtest_to']) if params.get('backtest_to') else None
        df = slice_by_time(df, start_ms, end_ms)
        print(f"[INFO] 切片后 {len(df):,} 条K线")
        
        # 加载策略
        print(f"[INFO] 加载策略: {args.strategy}")
        StrategyCls = load_strategy(args.strategy)
        
        # 运行回测
        use_parallel = not args.no_parallel and len(df) > 10000
        
        if use_parallel:
            workers = args.workers or max(1, mp.cpu_count() - 1)
            print(f"[INFO] 使用并行模式 ({workers} workers)")
            result = run_parallel(df, StrategyCls, params, workers, args.strategy)
            equity = result['equity_curve']
        else:
            print(f"[INFO] 使用串行模式")
            engine = Engine(StrategyCls, params, df)
            engine.run()
            equity = engine.equity_curve
        
        # 导出结果
        export_results(dated_dir, df, equity, params)
        
        print("\n[完成] 回测完成!")


if __name__ == '__main__':
    main()
