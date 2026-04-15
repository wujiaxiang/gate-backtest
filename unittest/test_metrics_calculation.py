#!/usr/bin/env python3
"""
回测指标计算单元测试

测试策略：
1. 简单做多：价格从 100 涨到 110，涨幅 10%
2. 简单做空：价格从 100 跌到 90，跌幅 -10%
3. 带杠杆：2x 杠杆做多，价格涨 10%
4. 带杠杆：3x 杠杆做空，价格跌 10%

验证各项指标是否符合预期
"""

import unittest
import json
from datetime import datetime, timedelta

# 简化的指标计算函数（用于测试）
def calculate_metrics_simple(prices, leverage=1, direction='long', initial_capital=1000):
    """
    简化的指标计算，用于验证逻辑
    """
    if len(prices) < 2:
        return {}
    
    # 价格变化
    price_change_pct = (prices[-1] - prices[0]) / prices[0] * 100
    
    # 根据方向计算收益率
    if direction == 'long':
        return_pct = price_change_pct * leverage
    elif direction == 'short':
        return_pct = -price_change_pct * leverage
    else:
        return_pct = 0
    
    # 收益金额
    return_amount = initial_capital * return_pct / 100
    
    # 最终资金
    final_capital = initial_capital + return_amount
    
    # 计算每日收益率（用于其他指标）
    daily_returns = []
    for i in range(1, len(prices)):
        if direction == 'long':
            dr = (prices[i] - prices[i-1]) / prices[i-1] * leverage * 100
        else:
            dr = -(prices[i] - prices[i-1]) / prices[i-1] * leverage * 100
        daily_returns.append(dr)
    
    # 最大回撤
    cumulative = [100]  # 从100%开始
    peak = 100
    max_drawdown = 0
    for dr in daily_returns:
        cumulative.append(cumulative[-1] * (1 + dr/100))
        if cumulative[-1] > peak:
            peak = cumulative[-1]
        dd = (peak - cumulative[-1]) / peak * 100
        if dd > max_drawdown:
            max_drawdown = dd
    
    # 波动率（年化）
    import statistics
    if len(daily_returns) > 1:
        vol = statistics.stdev(daily_returns) * (252 ** 0.5)
    else:
        vol = 0
    
    # 夏普比率
    if vol > 0:
        sharpe = sum(daily_returns) / len(daily_returns) / vol
    else:
        sharpe = 0
    
    # 胜率
    wins = sum(1 for r in daily_returns if r > 0)
    win_rate = wins / len(daily_returns) * 100 if daily_returns else 0
    
    return {
        'price_change_pct': round(price_change_pct, 2),
        'return_pct': round(return_pct, 2),
        'return_amount': round(return_amount, 2),
        'final_capital': round(final_capital, 2),
        'max_drawdown_pct': round(max_drawdown, 2),
        'volatility_pct': round(vol, 2),
        'sharpe_ratio': round(sharpe, 2),
        'win_rate_pct': round(win_rate, 2),
        'leverage': leverage,
        'direction': direction,
        'initial_capital': initial_capital
    }


class TestBacktestMetrics(unittest.TestCase):
    """回测指标计算测试"""
    
    def test_long_no_leverage(self):
        """测试：做多，无杠杆，价格涨 10%"""
        prices = [100, 105, 110]  # 涨到 110，涨幅 10%
        result = calculate_metrics_simple(prices, leverage=1, direction='long')
        
        print("\n" + "="*50)
        print("测试1: 做多，无杠杆，价格涨 10%")
        print("="*50)
        print(f"价格: 100 → 110 (涨幅 10%)")
        print(f"结果: {json.dumps(result, indent=2)}")
        
        self.assertEqual(result['price_change_pct'], 10.0)
        self.assertEqual(result['return_pct'], 10.0)  # 10% * 1x = 10%
        self.assertEqual(result['return_amount'], 100.0)  # 1000 * 10% = 100
        self.assertEqual(result['final_capital'], 1100.0)
    
    def test_short_no_leverage(self):
        """测试：做空，无杠杆，价格跌 10%"""
        prices = [100, 95, 90]  # 跌到 90，跌幅 -10%
        result = calculate_metrics_simple(prices, leverage=1, direction='short')
        
        print("\n" + "="*50)
        print("测试2: 做空，无杠杆，价格跌 10%")
        print("="*50)
        print(f"价格: 100 → 90 (跌幅 -10%)")
        print(f"结果: {json.dumps(result, indent=2)}")
        
        self.assertEqual(result['price_change_pct'], -10.0)
        self.assertEqual(result['return_pct'], 10.0)  # -(-10%) * 1x = 10%
        self.assertEqual(result['return_amount'], 100.0)  # 1000 * 10% = 100
        self.assertEqual(result['final_capital'], 1100.0)
    
    def test_long_with_leverage(self):
        """测试：做多，2x杠杆，价格涨 10%"""
        prices = [100, 105, 110]  # 涨到 110，涨幅 10%
        result = calculate_metrics_simple(prices, leverage=2, direction='long')
        
        print("\n" + "="*50)
        print("测试3: 做多，2x杠杆，价格涨 10%")
        print("="*50)
        print(f"价格: 100 → 110 (涨幅 10%)")
        print(f"结果: {json.dumps(result, indent=2)}")
        
        self.assertEqual(result['price_change_pct'], 10.0)
        self.assertEqual(result['return_pct'], 20.0)  # 10% * 2x = 20%
        self.assertEqual(result['return_amount'], 200.0)  # 1000 * 20% = 200
        self.assertEqual(result['final_capital'], 1200.0)
    
    def test_short_with_leverage(self):
        """测试：做空，3x杠杆，价格跌 10%"""
        prices = [100, 95, 90]  # 跌到 90，跌幅 -10%
        result = calculate_metrics_simple(prices, leverage=3, direction='short')
        
        print("\n" + "="*50)
        print("测试4: 做空，3x杠杆，价格跌 10%")
        print("="*50)
        print(f"价格: 100 → 90 (跌幅 -10%)")
        print(f"结果: {json.dumps(result, indent=2)}")
        
        self.assertEqual(result['price_change_pct'], -10.0)
        self.assertEqual(result['return_pct'], 30.0)  # -(-10%) * 3x = 30%
        self.assertEqual(result['return_amount'], 300.0)  # 1000 * 30% = 300
        self.assertEqual(result['final_capital'], 1300.0)
    
    def test_short_loss_with_leverage(self):
        """测试：做空，2x杠杆，价格涨 10%（做空亏损）"""
        prices = [100, 105, 110]  # 涨到 110，涨幅 10%
        result = calculate_metrics_simple(prices, leverage=2, direction='short')
        
        print("\n" + "="*50)
        print("测试5: 做空，2x杠杆，价格涨 10%（做空亏损）")
        print("="*50)
        print(f"价格: 100 → 110 (涨幅 10%)")
        print(f"结果: {json.dumps(result, indent=2)}")
        
        self.assertEqual(result['price_change_pct'], 10.0)
        self.assertEqual(result['return_pct'], -20.0)  # -(10%) * 2x = -20%
        self.assertEqual(result['return_amount'], -200.0)  # 1000 * -20% = -200
        self.assertEqual(result['final_capital'], 800.0)
    
    def test_real_backtest_data(self):
        """测试：使用真实回测数据片段"""
        # ETH 做空 50x，价格从 3335 跌到 2499
        prices = [3335.1, 3000.0, 2700.0, 2499.3]
        leverage = 50
        result = calculate_metrics_simple(prices, leverage=leverage, direction='short', initial_capital=200)
        
        price_change = (2499.3 - 3335.1) / 3335.1 * 100
        expected_return = -price_change * leverage
        
        print("\n" + "="*50)
        print("测试6: 真实回测数据片段")
        print("="*50)
        print(f"价格: 3335.1 → 2499.3 (跌幅 {price_change:.2f}%)")
        print(f"杠杆: {leverage}x")
        print(f"方向: 做空")
        print(f"期望收益率: {expected_return:.2f}%")
        print(f"结果: {json.dumps(result, indent=2)}")
        
        self.assertAlmostEqual(result['price_change_pct'], price_change, places=1)
        self.assertAlmostEqual(result['return_pct'], expected_return, places=1)
        
        # 期望收益率约为 1253%
        self.assertGreater(result['return_pct'], 1000)
        self.assertLess(result['return_pct'], 1500)


class TestRealBacktestData(unittest.TestCase):
    """使用真实回测数据验证"""
    
    @classmethod
    def setUpClass(cls):
        """加载真实数据"""
        try:
            with open('/Users/wujiaxiang/CodeBuddy/Claw/gate-backtest/results/20260415_190739/backtest_result.json', 'r') as f:
                cls.real_data = json.load(f)
        except FileNotFoundError:
            cls.real_data = None
    
    def test_real_data_metrics(self):
        """验证真实数据的指标"""
        if not self.real_data:
            self.skipTest("真实数据文件不存在")
        
        data = self.real_data
        equity = data['data_series']['equity']
        params = data['backtest_params']
        metrics = data['key_metrics']
        
        # 提取价格序列
        prices = [e['price'] for e in equity]
        
        # 用简化函数重新计算
        result = calculate_metrics_simple(
            prices,
            leverage=params['leverage'],
            direction=params['direction'],
            initial_capital=params['investment']
        )
        
        print("\n" + "="*60)
        print("真实回测数据对比")
        print("="*60)
        print(f"参数: {params['direction']} {params['leverage']}x")
        print(f"价格: ${prices[0]} → ${prices[-1]}")
        print()
        print(f"{'指标':<20} {'报告值':>15} {'计算值':>15} {'差异':>10}")
        print("-" * 60)
        
        # 对比各项指标
        comparisons = [
            ('price_change_pct', 'price_change_pct'),
            ('return_pct', 'total_return_pct'),
        ]
        
        for calc_key, report_key in comparisons:
            calc_val = result.get(calc_key, 0)
            report_val = metrics.get(report_key, 0)
            diff = calc_val - report_val
            match = "✓" if abs(diff) < 1 else "✗"
            print(f"{calc_key:<20} {report_val:>15.2f} {calc_val:>15.2f} {diff:>+10.2f} {match}")
        
        print()
        print(f"简化函数计算的 return_pct: {result['return_pct']:.2f}%")
        print(f"真实应该的收益率: {result['return_pct']:.2f}% (考虑杠杆和方向)")
        print(f"报告的 total_return_pct: {metrics['total_return_pct']:.2f}% (未考虑杠杆)")


def generate_test_json():
    """生成测试用的 JSON 文件"""
    import os
    
    # 生成简单测试数据
    prices = [100, 102, 105, 103, 108, 110]  # 涨 10%
    result = calculate_metrics_simple(prices, leverage=2, direction='long', initial_capital=1000)
    
    # 构建 equity 数据
    equity = []
    base_time = datetime(2025, 1, 1, 0, 0, 0)
    for i, price in enumerate(prices):
        equity.append({
            "time": (base_time + timedelta(minutes=i)).isoformat() + "+00:00",
            "price": price,
            "position": 0.1
        })
    
    test_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "source": "gate-backtest-test"
        },
        "backtest_params": {
            "market": "TEST_USDT",
            "interval": "1m",
            "backtest_from": "2025-01-01",
            "backtest_to": "2025-01-02",
            "investment": 1000.0,
            "leverage": 2,
            "direction": "long",
            "data_source": "test",
            "commission": 0.0002
        },
        "key_metrics": result,
        "data_series": {
            "equity": equity,
            "trades": [],
            "sample_size": len(equity)
        }
    }
    
    # 保存测试文件
    test_dir = '/Users/wujiaxiang/CodeBuddy/Claw/gate-backtest/html'
    os.makedirs(test_dir, exist_ok=True)
    
    test_path = os.path.join(test_dir, 'test_metrics.json')
    with open(test_path, 'w') as f:
        json.dump(test_data, f, indent=2)
    
    print(f"\n测试数据已保存到: {test_path}")
    print(json.dumps(test_data, indent=2))


if __name__ == '__main__':
    print("=" * 60)
    print("回测指标计算单元测试")
    print("=" * 60)
    
    # 生成测试数据
    generate_test_json()
    
    # 运行单元测试
    print("\n\n")
    unittest.main(verbosity=2)
