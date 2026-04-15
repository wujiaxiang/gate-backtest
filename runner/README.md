# 引擎架构说明

本目录包含回测引擎的核心代码模块。

## 目录结构

```
runner/
├── README.md              # 本文档
├── __init__.py            # 包初始化
├── backtest.py            # 回测引擎核心
├── engine.py              # 回测引擎入口
├── data.py                # 数据获取模块
├── adapters/              # 交易所适配器
│   ├── __init__.py
│   ├── base.py            # 基础适配器
│   ├── gate.py            # Gate.io 适配器
│   ├── gate_history.py    # Gate.io 历史数据适配器
│   ├── binance.py          # 币安适配器
│   └── okx.py             # OKX 适配器
├── strategies/            # 策略模块
│   ├── __init__.py
│   ├── base.py            # 基础策略类
│   ├── martingale.py       # 内置马丁格尔策略
│   └── user_strategy.py    # 用户策略基类
└── utils/                  # 工具函数
    ├── __init__.py
    ├── indicators.py       # 技术指标计算
    └── metrics.py         # 绩效指标计算
```

## 核心模块

### backtest.py - 回测引擎核心

负责回测的核心逻辑：

1. 逐K线迭代执行策略
2. 仓位管理（开仓、平仓、加仓）
3. 盈亏计算
4. 订单管理

**主要类**：`BacktestCore`

### engine.py - 回测引擎入口

高层封装，提供简洁的 API：

```python
from gate_backtest import BacktestEngine

engine = BacktestEngine(
    strategy_class=MyStrategy,
    initial_cash=1000,
    commission=0.0005
)

result = engine.run(data)
engine.print_report(result)
```

### data.py - 数据获取模块

提供统一的数据获取接口：

```python
from gate_backtest.data import DataFetcher

fetcher = DataFetcher('gate_history')
data = fetcher.fetch_ohlcv(
    symbol='ETH/USDT',
    interval='1d',
    start_date='2025-01-01',
    end_date='2026-04-15'
)
```

## 适配器模式

### 设计理念

采用适配器模式，统一不同交易所的数据接口：

```
数据请求
    │
    ▼
DataFetcher (统一接口)
    │
    ▼
Adapter (适配器层)
    │
    ├── GateAdapter (Gate.io)
    ├── GateHistoryAdapter (Gate.io 历史)
    ├── BinanceAdapter (币安)
    └── OKXAdapter (OKX)
```

### 添加新交易所

1. 在 `adapters/` 目录创建新适配器文件
2. 继承 `BaseAdapter` 类
3. 实现 `fetch_ohlcv` 方法

```python
from .base import BaseAdapter

class NewExchangeAdapter(BaseAdapter):
    """新交易所适配器"""
    
    def __init__(self):
        super().__init__('new_exchange')
    
    def fetch_ohlcv(self, symbol, interval, start_date, end_date):
        # 实现数据获取逻辑
        pass
```

## 策略模块

### base.py - 基础策略类

所有策略的基类，定义策略接口：

```python
class BaseStrategy:
    params = {}  # 策略参数
    
    def __init__(self):
        """初始化"""
        pass
    
    def next(self, context):
        """每根K线执行一次"""
        pass
```

### user_strategy.py - 用户策略基类

用户编写策略时继承的基类：

```python
from gate_backtest.strategies import UserStrategy

class MyStrategy(UserStrategy):
    def __init__(self):
        self.order = None
    
    def next(self, get_klines_func, sell_func, close_func, position):
        # 策略逻辑
        pass
```

## 工具模块

### utils/indicators.py - 技术指标

预计算的技术指标，包括：

- RSI (相对强弱指数)
- ATR (平均真实波幅)
- MACD
- 布林带
- 均线系列

### utils/metrics.py - 绩效指标

回测绩效计算，包括：

- 总收益率
- 年化收益率
- 最大回撤
- 夏普比率
- 胜率
- 波动率

## 数据流

```
1. 数据获取
   用户配置 → DataFetcher → Adapter → Exchange API
   
2. 数据预处理
   Raw Data → 格式转换 → 预计算指标 → 传递给引擎
   
3. 回测执行
   K线数据 → 引擎遍历 → 策略判断 → 订单执行 → 仓位更新
   
4. 结果输出
   回测数据 → 绩效计算 → JSON/CSV 导出 → HTML 报告
```

## 性能优化

### 已实现的优化

1. **预计算指标**：RSI、ATR 等指标在回测开始前一次性计算
2. **TalibProxy 代理**：拦截 TA-Lib 调用，实现向量化计算
3. **并行回测**：按月份分割数据，多进程并行执行

### 扩展优化

如需进一步优化，可考虑：

1. **Numba JIT 编译**：对计算密集型代码使用 Numba 加速
2. **数据分片**：对超长回测周期进行数据分片
3. **缓存机制**：缓存常用指标计算结果

## 相关文档

- [根目录 README](../README.md)
- [策略示例 + 教程](../examples/)
- [单元测试](../unittest/)
