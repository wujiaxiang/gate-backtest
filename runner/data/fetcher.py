"""
数据获取模块 - 支持 Gate.io、币安等多个交易所
以及 Gate.io 历史批量数据下载
"""

import os
import pandas as pd
from datetime import datetime
from typing import Optional, Literal
import time

from .gate_histor import GateHistoricalDownloader


class DataFetcher:
    """
    统一数据获取接口

    支持交易所: gate, binance, okx, hyperliquid
    支持 Gate 历史批量数据: gate_history
    """

    SUPPORTED_EXCHANGES = ['gate', 'binance', 'okx', 'hyperliquid', 'gate_history']
    SUPPORTED_INTERVALS = {
        '1m': '1m', '5m': '5m', '15m': '15m',
        '1h': '1h', '4h': '4h', '1d': '1d', '1w': '1w'
    }

    def __init__(self, exchange: str = 'gate', data_dir: str = 'data/gate_history'):
        """
        初始化数据获取器

        Args:
            exchange:  交易所名称或数据源类型
                       - 'gate':       Gate.io 永续合约 (ccxt)
                       - 'binance':    币安 (ccxt)
                       - 'okx':        OKX (ccxt)
                       - 'hyperliquid': Hyperliquid (ccxt)
                       - 'gate_history': Gate.io 历史批量数据 (download.gatedata.org)
            data_dir:  Gate 历史数据本地缓存目录
        """
        self.exchange_name = exchange.lower()
        self._exchange = None
        self._gate_histor: Optional[GateHistoricalDownloader] = None
        self.data_dir = data_dir
        self._init_exchange()

    def _init_exchange(self):
        """初始化交易所连接"""
        if self.exchange_name == 'gate_history':
            # Gate 历史批量数据不需要 ccxt
            self._gate_histor = GateHistoricalDownloader(data_dir=self.data_dir)
            return

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

    def set_biz_type(self, biz: str = 'futures_usdt'):
        """
        设置 Gate 历史数据的业务类型 (仅 gate_history 模式有效)

        Args:
            biz: 'spot', 'futures_usdt', 'futures_btc'
        """
        if self.exchange_name == 'gate_history':
            self._gate_histor = GateHistoricalDownloader(biz=biz, data_dir=self.data_dir)

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: Optional[str] = None,
        limit: int = 1000,
        output_file: Optional[str] = None,
        biz: str = 'futures_usdt',
    ) -> pd.DataFrame:
        """
        获取K线数据 (统一接口，兼容 gate_history 模式)

        Args:
            symbol:     交易对，如 'ETH/USDT' 或 'ETH_USDT'
            interval:   K线周期，如 '1d', '4h', '1h', '1m', '5m', '7d'
            start_date: 开始日期 'YYYY-MM-DD'
            end_date:   结束日期 'YYYY-MM-DD'
            limit:      每次请求的最大条数 (仅 ccxt 模式有效)
            output_file: 保存到本地文件
            biz:        Gate 历史数据业务类型 ['spot', 'futures_usdt', 'futures_btc']
                       仅 gate_history 模式有效

        Returns:
            DataFrame 格式的K线数据，列名: timestamp, o, h, l, c, v
        """
        # gate_history 模式: 使用 Gate 批量下载 API
        if self.exchange_name == 'gate_history':
            market = symbol.replace('/', '_').replace('-', '_')
            df = self._gate_histor.download_ohlcv(
                market=market,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                output_file=output_file,
                verbose=True,
            )
            return df

        # ccxt 模式
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

    def load_local(
        self,
        filepath: str,
        symbol: Optional[str] = None,
        interval: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        从本地CSV文件加载K线数据

        支持多种格式:
        - 标准格式 (timestamp 索引): timestamp,o,h,l,c,v
        - Gate 历史数据格式 (timestamp 列): timestamp,o,h,l,c,v
        - Gate 历史数据 .csv.gz 压缩文件
        - 带表头的 CSV: timestamp,open,high,low,close,volume

        Args:
            filepath: CSV文件路径 (支持 .gz 压缩)
            symbol:   交易对 (如 'ETH_USDT')，用于 gate_history 模式
            interval: K线周期 (如 '1d')，用于 gate_history 模式

        Returns:
            DataFrame 格式的K线数据，列名: timestamp, o, h, l, c, v
        """
        import gzip

        if not os.path.exists(filepath):
            # gate_history 模式: 尝试从数据目录加载
            if self.exchange_name == 'gate_history' and symbol and interval:
                print(f"[数据加载] 本地文件不存在，尝试从缓存目录加载: {filepath}")
                df = self._gate_histor.load_local(
                    market=symbol.replace('/', '_'),
                    interval=interval,
                    verbose=True,
                )
                return df
            raise FileNotFoundError(f"本地数据文件不存在: {filepath}")

        # 自动检测 .gz 压缩文件
        if filepath.endswith('.gz'):
            return self._load_gz_csv(filepath)

        try:
            # 尝试标准格式 (timestamp 为索引)
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        except Exception:
            # 尝试带时间列的格式
            df = pd.read_csv(filepath, parse_dates=['timestamp'])
            if 'timestamp' not in df.columns:
                df = pd.read_csv(filepath)

        # 标准化列名
        df = self._normalize_columns(df)

        print(f"[数据加载] 从 {filepath} 加载 {len(df)} 条数据")
        return df

    def _load_gz_csv(self, filepath: str) -> pd.DataFrame:
        """加载 .csv.gz 压缩文件"""
        import gzip
        try:
            with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                first_line = f.readline().strip()

            # 检测是否有表头
            has_header = ',' in first_line and not first_line[:10].replace('-', '').replace('.', '').isdigit()

            if has_header:
                df = pd.read_csv(filepath, compression='gzip', parse_dates=['timestamp'])
            else:
                df = pd.read_csv(
                    filepath, compression='gzip',
                    header=None,
                    names=['timestamp', 'o', 'h', 'l', 'c', 'v']
                )
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')

            df = self._normalize_columns(df)
            return df
        except Exception as e:
            raise RuntimeError(f"加载 .gz 文件失败 {filepath}: {e}")

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化 DataFrame 列名"""
        rename_map = {
            'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c', 'volume': 'v',
            'Open': 'o', 'High': 'h', 'Low': 'l', 'Close': 'c', 'Volume': 'v',
            't': 'timestamp', 'Time': 'timestamp', 'time': 'timestamp',
        }
        df = df.rename(columns=rename_map)

        for col in ['o', 'h', 'l', 'c', 'v']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 确保有 timestamp 列
        if 'timestamp' not in df.columns:
            if df.index.name and 'time' in df.index.name.lower():
                df.index.name = 'timestamp'
            elif len(df.columns) >= 6:
                df = df.rename(columns={df.columns[0]: 'timestamp'})
            else:
                df = df.rename(columns={df.columns[0]: 'timestamp'})

        if 'timestamp' in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        return df
