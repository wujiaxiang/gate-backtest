#!/usr/bin/env python3
"""
Gate-Backtest 运行脚本

用法:
    python scripts/run_backtest.py --config configs/params.json
    python scripts/run_backtest.py --symbol ETH/USDT --interval 1d --from 2025-01-01 --to 2026-04-15
"""

import argparse
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from runner import BacktestEngine, UserStrategy
from runner.data import DataFetcher
from runner.utils import load_params, validate_params


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Gate-Backtest: Gate.io量化策略回测框架',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--config', '-c',
        help='配置文件路径 (JSON)'
    )

    # 数据参数
    parser.add_argument(
        '--symbol', '-s',
        default='ETH/USDT',
        help='交易对 (如 ETH/USDT)'
    )
    parser.add_argument(
        '--interval', '-i',
        default='1d',
        help='K线周期 (1m, 5m, 15m, 1h, 4h, 1d, 1w)'
    )
    parser.add_argument(
        '--from',
        dest='from_date',
        help='回测开始日期 (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--to',
        dest='to_date',
        help='回测结束日期 (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--exchange', '-e',
        default='gate',
        choices=['gate', 'binance', 'okx', 'hyperliquid'],
        help='交易所'
    )
    parser.add_argument(
        '--data-file',
        help='使用本地CSV数据文件'
    )

    # 策略参数
    parser.add_argument(
        '--investment', '-m',
        type=float,
        help='初始投资金额 (USDT)'
    )
    parser.add_argument(
        '--leverage', '-l',
        type=int,
        help='杠杆倍数'
    )

    # 输出参数
    parser.add_argument(
        '--output', '-o',
        default='results',
        help='结果输出目录'
    )
    parser.add_argument(
        '--plot', '-p',
        action='store_true',
        help='生成回测图表'
    )
    parser.add_argument(
        '--save-data',
        action='store_true',
        help='保存获取的数据'
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 加载配置
    params = {}
    if args.config:
        params = load_params(args.config)

    # 命令行参数覆盖
    if args.from_date:
        params['backtest_from'] = args.from_date
    if args.to_date:
        params['backtest_to'] = args.to_date
    if args.investment:
        params['investment'] = args.investment
    if args.leverage:
        params['leverage'] = args.leverage

    # 默认参数
    params.setdefault('market', args.symbol.replace('/', '_'))
    params.setdefault('interval', args.interval)
    params.setdefault('backtest_from', '2025-01-01')
    params.setdefault('backtest_to', '2026-04-15')
    params.setdefault('investment', 1000)
    params.setdefault('leverage', 50)
    params.setdefault('commission', 0.0005)

    # 验证参数
    if not validate_params(params):
        sys.exit(1)

    print("=" * 60)
    print("Gate-Backtest 回测框架")
    print("=" * 60)
    print(f"交易对: {args.symbol}")
    print(f"周期: {args.interval}")
    print(f"时间范围: {params['backtest_from']} 至 {params['backtest_to']}")
    print(f"交易所: {args.exchange}")
    print(f"初始投资: {params['investment']} USDT")
    print(f"杠杆: {params['leverage']}x")
    print("-" * 60)

    # 获取数据
    if args.data_file and os.path.exists(args.data_file):
        print(f"[数据] 从本地文件加载: {args.data_file}")
        fetcher = DataFetcher(args.exchange)
        data = fetcher.load_local(args.data_file)
    else:
        print(f"[数据] 从 {args.exchange} 获取数据...")
        fetcher = DataFetcher(args.exchange)

        output_file = None
        if args.save_data:
            os.makedirs('data', exist_ok=True)
            symbol_clean = args.symbol.replace('/', '_')
            output_file = f'data/{symbol_clean}_{args.interval}.csv'

        data = fetcher.fetch_ohlcv(
            symbol=args.symbol,
            interval=args.interval,
            start_date=params['backtest_from'],
            end_date=params['backtest_to'],
            output_file=output_file
        )

        if data is None:
            print("[错误] 数据获取失败")
            sys.exit(1)

    # 运行回测
    print("[回测] 初始化引擎...")
    engine = BacktestEngine(
        strategy_class=UserStrategy,
        params=params,
        initial_cash=params['investment'],
        commission=params['commission']
    )

    print("[回测] 运行回测...")
    result = engine.run(
        data=data,
        plot=args.plot,
        output_dir=args.output
    )

    # 打印报告
    engine.print_report(result)

    print("\n[完成] 回测完成!")
    print(f"[提示] 交易记录保存在: {args.output}/trades.csv")


if __name__ == '__main__':
    main()
