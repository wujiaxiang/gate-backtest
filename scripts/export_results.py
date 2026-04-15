#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果导出脚本 - 将回测CSV结果转换为JSON格式

功能：
1. 读取 equity.csv 和 klines.csv
2. 计算回测关键指标（收益率、最大回撤、夏普比率等）
3. 生成标准化JSON结果文件
4. 提供HTML可视化所需的数据格式
"""

import os
import json
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional


def load_equity_data(csv_path: str) -> pd.DataFrame:
    """加载equity.csv数据"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"equity.csv文件不存在: {csv_path}")
    
    df = pd.read_csv(csv_path)
    # 确保时间列是datetime类型
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])
    elif 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.rename(columns={'timestamp': 'time'}, inplace=True)
    
    # 按时间排序
    df = df.sort_values('time').reset_index(drop=True)
    return df


def load_klines_data(csv_path: str) -> pd.DataFrame:
    """加载klines.csv数据"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"klines.csv文件不存在: {csv_path}")
    
    df = pd.read_csv(csv_path)
    # 确保时间列是datetime类型
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])
    elif 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.rename(columns={'timestamp': 'time'}, inplace=True)
    
    # 按时间排序
    df = df.sort_values('time').reset_index(drop=True)
    return df


def calculate_key_metrics(equity_df: pd.DataFrame, klines_df: pd.DataFrame, 
                         initial_capital: float = 1000) -> Dict[str, Any]:
    """
    计算回测关键指标
    
    参数:
        equity_df: 资产数据，包含time和close列
        klines_df: K线数据，包含time, close列
        initial_capital: 初始资本
    
    返回:
        包含各项指标的字典
    """
    if equity_df.empty:
        return {}
    
    # 使用equity数据中的价格序列
    prices = equity_df['close'].values.astype(float)
    times = equity_df['time'].values
    
    # 确保价格序列有效
    if len(prices) < 2:
        return {
            "total_return_pct": 0.0,
            "annual_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "volatility_pct": 0.0,
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
        }
    
    # 计算收益率序列
    returns = np.diff(prices) / prices[:-1]
    
    # 总收益率（基于价格变动）
    total_return_pct = ((prices[-1] - prices[0]) / prices[0]) * 100
    
    # 年化收益率
    days = (times[-1] - times[0]).days if hasattr(times[-1], 'days') else 365 * 2
    years = max(days / 365.0, 0.1)  # 避免除零
    annual_return_pct = ((1 + total_return_pct/100) ** (1/years) - 1) * 100
    
    # 最大回撤
    cumulative = np.maximum.accumulate(prices)
    drawdowns = (cumulative - prices) / cumulative
    max_drawdown_pct = drawdowns.max() * 100 if len(drawdowns) > 0 else 0.0
    
    # 波动率（年化）
    daily_volatility = np.std(returns) if len(returns) > 0 else 0
    volatility_pct = daily_volatility * np.sqrt(252) * 100
    
    # 夏普比率（假设无风险利率为0）
    sharpe_ratio = (np.mean(returns) * 252 / np.std(returns)) if np.std(returns) > 0 else 0
    
    # 计算交易统计（简化版本）
    # 从equity数据中检测仓位变化作为交易信号
    if 'position_size' in equity_df.columns:
        position = equity_df['position_size'].values
        position_changes = np.diff(position)
        total_trades = int(np.sum(np.abs(position_changes) > 0) / 2)  # 粗略估计
    else:
        total_trades = 0
    
    # 胜率（简化：假设价格上升为盈利）
    winning_days = np.sum(returns > 0)
    total_days = len(returns)
    win_rate_pct = (winning_days / total_days * 100) if total_days > 0 else 0
    
    # 盈利因子（总盈利/总亏损）
    positive_returns = returns[returns > 0]
    negative_returns = returns[returns < 0]
    total_profit = np.sum(positive_returns) if len(positive_returns) > 0 else 0
    total_loss = abs(np.sum(negative_returns)) if len(negative_returns) > 0 else 0
    profit_factor = total_profit / total_loss if total_loss > 0 else (0 if total_profit == 0 else 999)
    
    return {
        "total_return_pct": float(round(total_return_pct, 2)),
        "annual_return_pct": float(round(annual_return_pct, 2)),
        "max_drawdown_pct": float(round(max_drawdown_pct, 2)),
        "sharpe_ratio": float(round(sharpe_ratio, 2)),
        "volatility_pct": float(round(volatility_pct, 2)),
        "total_trades": int(total_trades),
        "win_rate_pct": float(round(win_rate_pct, 2)),
        "profit_factor": float(round(profit_factor, 2)),
        "final_price": float(round(prices[-1], 2)),
        "initial_price": float(round(prices[0], 2)),
        "price_change_pct": float(round(((prices[-1] - prices[0]) / prices[0]) * 100, 2)),
    }


def prepare_equity_series(equity_df: pd.DataFrame) -> List[Dict]:
    """准备资产数据序列，用于图表展示"""
    if equity_df.empty:
        return []
    
    # 确保有必要的列
    df = equity_df.copy()
    if 'close' not in df.columns and 'price' in df.columns:
        df.rename(columns={'price': 'close'}, inplace=True)
    
    # 转换为前端友好的格式
    series = []
    for _, row in df.iterrows():
        item = {
            "time": row['time'].isoformat() if hasattr(row['time'], 'isoformat') else str(row['time']),
            "price": float(row['close']) if 'close' in row else 0.0,
        }
        
        if 'position_size' in row:
            item["position"] = float(row['position_size'])
        
        series.append(item)
    
    return series


def prepare_trade_positions(equity_df: pd.DataFrame) -> List[Dict]:
    """从资产数据中提取交易位置（简化版本）"""
    if equity_df.empty or 'position_size' not in equity_df.columns:
        return []
    
    trades = []
    position = equity_df['position_size'].values
    
    # 找出仓位变化的点
    for i in range(1, len(position)):
        if position[i] != position[i-1]:
            trade = {
                "time": equity_df.iloc[i]['time'].isoformat() if hasattr(equity_df.iloc[i]['time'], 'isoformat') else str(equity_df.iloc[i]['time']),
                "price": float(equity_df.iloc[i]['close']) if 'close' in equity_df.columns else 0.0,
                "position": float(position[i]),
                "type": "open" if abs(position[i]) > abs(position[i-1]) else "close",
            }
            trades.append(trade)
    
    return trades


def generate_json_result(
    equity_df: pd.DataFrame,
    klines_df: pd.DataFrame,
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """生成最终JSON结果结构"""
    
    # 计算关键指标
    initial_capital = params.get('investment', 1000)
    metrics = calculate_key_metrics(equity_df, klines_df, initial_capital)
    
    # 准备数据序列
    equity_series = prepare_equity_series(equity_df)
    trade_positions = prepare_trade_positions(equity_df)
    
    # 构建完整结果
    result = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "source": "gate-backtest",
        },
        "backtest_params": {
            "market": params.get('market', 'ETH_USDT'),
            "interval": params.get('interval', '1d'),
            "backtest_from": params.get('backtest_from', '2023-01-01'),
            "backtest_to": params.get('backtest_to', '2025-12-31'),
            "investment": float(params.get('investment', 1000)),
            "leverage": int(params.get('leverage', 50)),
            "direction": params.get('direction', 'short'),
            "data_source": params.get('datasource', 'gate_history'),
            "commission": float(params.get('commission', 0.0005)),
        },
        "key_metrics": metrics,
        "data_series": {
            "equity": equity_series,
            "trades": trade_positions,
            "sample_size": len(equity_series),
        },
        "performance_summary": {
            "total_days": len(equity_df),
            "data_points": len(equity_series),
            "execution_time": params.get('execution_time', 0),
        }
    }
    
    return result


def save_json_result(result_dict: Dict[str, Any], output_path: str) -> str:
    """保存JSON文件，返回文件路径"""
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)
    
    print(f"[EXPORT] JSON结果已保存到: {output_path}")
    print(f"[EXPORT] 包含 {result_dict['data_series']['sample_size']} 个数据点")
    
    return output_path


def get_html_report_path() -> str:
    """获取HTML报告路径"""
    html_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'html')
    return os.path.join(html_dir, 'backtest_report.html')


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='回测结果导出工具')
    parser.add_argument('--equity', default='results/equity.csv', help='equity.csv文件路径')
    parser.add_argument('--klines', default='results/klines.csv', help='klines.csv文件路径')
    parser.add_argument('--output', default='results/backtest_result.json', help='输出JSON文件路径')
    parser.add_argument('--params', default='configs/params.json', help='参数配置文件')
    parser.add_argument('--investment', type=float, default=1000, help='初始投资金额')
    parser.add_argument('--leverage', type=int, default=50, help='杠杆倍数')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("回测结果导出工具")
    print("=" * 60)
    
    # 加载数据
    print("[INFO] 加载equity数据...")
    equity_df = load_equity_data(args.equity)
    print(f"[INFO] 加载 {len(equity_df)} 条equity记录")
    
    print("[INFO] 加载K线数据...")
    klines_df = load_klines_data(args.klines)
    print(f"[INFO] 加载 {len(klines_df)} 条K线记录")
    
    # 加载或构建参数
    params = {}
    if os.path.exists(args.params):
        with open(args.params, 'r', encoding='utf-8') as f:
            params = json.load(f)
        print(f"[INFO] 从 {args.params} 加载参数")
    else:
        print(f"[WARN] 参数文件 {args.params} 不存在，使用默认参数")
    
    # 更新参数
    params['investment'] = args.investment
    params['leverage'] = args.leverage
    
    # 从文件名推断参数
    if 'market' not in params:
        params['market'] = 'ETH_USDT'
    if 'interval' not in params:
        params['interval'] = '1d'
    if 'backtest_from' not in params and not equity_df.empty:
        params['backtest_from'] = equity_df['time'].iloc[0].strftime('%Y-%m-%d')
    if 'backtest_to' not in params and not equity_df.empty:
        params['backtest_to'] = equity_df['time'].iloc[-1].strftime('%Y-%m-%d')
    if 'direction' not in params:
        params['direction'] = 'short'
    if 'datasource' not in params:
        params['datasource'] = 'gate_history'
    
    # 生成JSON结果
    print("[INFO] 计算回测指标...")
    result = generate_json_result(equity_df, klines_df, params)
    
    # 保存结果
    save_json_result(result, args.output)
    
    # 打印汇总
    print("\n" + "=" * 60)
    print("回测指标汇总")
    print("=" * 60)
    metrics = result['key_metrics']
    for key, value in metrics.items():
        print(f"{key:20s}: {value}")
    
    # 显示HTML报告路径
    html_path = get_html_report_path()
    print("\n" + "=" * 60)
    print("HTML可视化报告")
    print("=" * 60)
    print(f"打开方式:")
    print(f"  1. 浏览器直接打开: file://{os.path.abspath(html_path)}")
    print(f"  2. 使用Python服务器: cd html && python -m http.server 8080")
    print(f"  3. 然后访问: http://localhost:8080/backtest_report.html")
    print("\n[完成] JSON导出完成!")


if __name__ == '__main__':
    main()