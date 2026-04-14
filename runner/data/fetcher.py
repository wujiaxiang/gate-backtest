"""
数据获取模块 - 支持 Gate.io、币安等多个交易所
"""

import pandas as pd
from datetime import datetime
from typing import Optional, Literal
import time


class DataFetcher:
    """
    统一数据获取接口

    支持交易所: gate, binance, okx, hyperliquid
    """

    SUPPORTED_EXCHANGES = ['gate', 'binance', 'okx', 'hyperliquid']
    SUPPORTED_INTERVALS = {
        '1m': '1m', '5m': '5m', '15m': '15m',
        '1h': '1h', '4h': '4h', '1d': '1d', '1w': '1w'
    }

    def __init__(self, exchange: str = 'gate'):
        """
        初始化数据获取器

        Args:
            exchange: 交易所名称
        """
        self.exchange_name = exchange.lower()
        self._exchange = None
        self._init_exchange()

    def _init_exchange(self):
        """初始化交易所连接"""
        try:
            import ccxt
        except ImportError:
            raise ImportError("请安装 ccxt: pip install ccxt")

        if self.exchange_name == 'gate':
            self._exchange = ccxt.gate({
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}  # 永续合约
            })
        elif self.exchange_name == 'binance':
            self._exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
        elif self.exchange_name == 'okx':
            self._exchange = ccxt.okx({
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })
        elif self.exchange_name == 'hyperliquid':
            self._exchange = ccxt.hyperliquid({
                'enableRateLimit': True
            })
        else:
            raise ValueError(f"不支持的交易所: {self.exchange_name}")

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: Optional[str] = None,
        limit: int = 1000,
        output_file: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取K线数据

        Args:
            symbol: 交易对，如 'ETH/USDT'
            interval: K线周期，如 '1d', '4h', '1h'
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            limit: 每次请求的最大条数
            output_file: 保存到本地文件

        Returns:
            DataFrame 格式的K线数据
        """
        print(f"[数据获取] 正在从 {self.exchange_name} 获取 {symbol} {interval} 数据...")

        # 转换日期为时间戳 (毫秒)
        since = int(pd.Timestamp(start_date).timestamp() * 1000)
        end_ts = int(pd.Timestamp(end_date or datetime.now().strftime('%Y-%m-%d')).timestamp() * 1000) if end_date else None

        all_data = []
        max_retries = 3

        while True:
            for attempt in range(max_retries):
                try:
                    ohlcv = self._exchange.fetch_ohlcv(symbol, interval, since, limit)
                    if not ohlcv:
                        print("[数据获取] 已到达数据末尾")
                        return self._process_data(all_data, output_file)

                    all_data.extend(ohlcv)
                    since = ohlcv[-1][0] + 1

                    print(f"[数据获取] 已获取 {len(all_data)} 条数据...")

                    # 检查是否到达结束时间
                    if end_ts and since > end_ts:
                        return self._process_data(all_data, output_file)

                    # 避免请求过于频繁
                    time.sleep(0.3)
                    break

                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"[数据获取] 请求异常: {e}, 等待重试...")
                        time.sleep(2)
                    else:
                        print(f"[数据获取] 获取失败: {e}")
                        return self._process_data(all_data, output_file)

            # 防止无限循环
            if not all_data or len(all_data) >= 10000:
                break

        return self._process_data(all_data, output_file)

    def _process_data(self, all_data: list, output_file: Optional[str] = None) -> pd.DataFrame:
        """处理数据"""
        if not all_data:
            print("[数据获取] 未获取到数据")
            return None

        # 转换为 DataFrame
        df = pd.DataFrame(all_data, columns=['timestamp', 'o', 'h', 'l', 'c', 'v'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        print(f"[数据获取] 共获取 {len(df)} 条K线数据")
        print(f"[数据获取] 时间范围: {df.index[0]} 至 {df.index[-1]}")

        # 保存到本地
        if output_file:
            df.to_csv(output_file)
            print(f"[数据获取] 已保存到 {output_file}")

        return df

    def load_local(self, filepath: str) -> pd.DataFrame:
        """
        从本地CSV文件加载数据

        Args:
            filepath: CSV文件路径

        Returns:
            DataFrame 格式的K线数据
        """
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        print(f"[数据加载] 从 {filepath} 加载 {len(df)} 条数据")
        return df
