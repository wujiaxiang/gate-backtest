"""
测试辅助工具
"""
import sys
import gzip
import tempfile
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))


def create_sample_klines(days=3, interval="1m") -> pd.DataFrame:
    """创建测试用的K线数据"""
    import numpy as np
    
    n = days * 1440 if interval == "1m" else days
    base_price = 3000.0
    
    times = []
    closes = []
    start_time = datetime(2025, 1, 1, 0, 0, 0)
    
    for i in range(n):
        t = start_time + timedelta(minutes=i)
        times.append(t.isoformat())
        close = base_price + np.random.randn() * 50
        closes.append(close)
        base_price = close * 0.9995 + 3000 * 0.0005
    
    df = pd.DataFrame({
        'time': times,
        'open': closes,
        'high': [c * 1.002 for c in closes],
        'low': [c * 0.998 for c in closes],
        'close': closes,
        'volume': [1000 + np.random.rand() * 500 for _ in range(n)]
    })
    
    return df


def create_test_csv(days=3, interval="1m") -> str:
    """创建测试CSV文件"""
    df = create_sample_klines(days, interval)
    fd, path = tempfile.mkstemp(suffix='.csv', prefix='test_klines_')
    os.close(fd)
    df.to_csv(path, index=False)
    return path


# 测试参数配置
TEST_PARAMS = {
    'market': 'ETH_USDT',
    'investment': 200,
    'leverage': 50,
    'rsi_period': 14,
    'rsi_upper': 70,
    'rsi_lower': 30,
    'atr_period': 14,
    'tp_atr_mult': 1.5,
    'sl_atr_mult': 0.5,
    'martingale_mult': 2,
    'max_martingale': 5,
    'compounding_ratio': 0.3,
    'base_quantity_ratio': 0.5,
}


def get_strategy_path():
    """获取策略文件路径"""
    return str(PROJECT_ROOT / 'runner' / 'strategies' / 'user_strategy.py')
