# 策略示例

本目录包含各种量化交易策略的示例代码和编写教程。

## 目录结构

```
examples/
├── README.md              # 本文档（策略教程 + 示例说明）
├── 01_simple_rsi.py       # 简单 RSI 策略
├── 02_ma_cross.py        # 均线交叉策略
├── 03_bollinger_bands.py  # 布林带策略
├── 04_grid_strategy.py   # 网格策略
└── 05_martingale.py       # 马丁格尔策略
```

---

# 策略编写教程

## 基础结构

每个策略文件都需要包含一个 `UserStrategy` 类：

```python
import numpy as np
import pandas as pd
import talib


class UserStrategy:
    """策略描述"""
    
    # 策略参数
    params = dict(
        rsi_period=14,
        rsi_oversold=30,
        rsi_overbought=70,
    )
    
    def __init__(self):
        """初始化"""
        self.order = None
        
    def next(self, get_klines_func, sell_func, close_func, position):
        """每根K线执行一次的核心逻辑"""
        pass
```

## 核心方法

### `next(get_klines_func, sell_func, close_func, position)`

每根 K 线触发一次，是策略的核心逻辑。

| 参数 | 类型 | 说明 |
|------|------|------|
| `get_klines_func` | function | 获取K线数据的函数 |
| `sell_func` | function | 开空仓（做空）的函数 |
| `close_func` | function | 平仓函数 |
| `position` | object | 持仓对象，含 `.size` 属性 |

## 数据获取

```python
def next(self, get_klines_func, ...):
    # 获取最近100根K线
    df = get_klines_func(limit=100, as_df=True)
    
    if df is None or df.empty:
        return
    
    # 数据列名: time, o, h, l, c, v
    close = df["c"]
    high = df["h"]
    low = df["l"]
```

### TA-Lib 技术指标

```python
import talib

# RSI
rsi = talib.RSI(close.values, timeperiod=14)

# 均线
ma = talib.MA(close.values, timeperiod=20)

# MACD
macd, signal, hist = talib.MACD(close.values)

# 布林带
upper, middle, lower = talib.BBANDS(close.values, timeperiod=20)

# ATR
atr = talib.ATR(high.values, low.values, close.values, timeperiod=14)
```

## 交易操作

### 开仓（做空）

```python
def next(self, get_klines_func, sell_func, close_func, position):
    if position.size == 0:  # 无持仓
        self.order = sell_func(size=1.0)
```

### 平仓

```python
def next(self, ...):
    if position.size != 0:  # 有持仓
        self.order = close_func()
```

### 订单状态追踪

```python
def __init__(self):
    self.order = None  # 初始无订单

def next(self, ...):
    if self.order:
        return  # 订单未成交，跳过
    
    # 下单逻辑
    self.order = sell_func(size=1.0)
```

## 参数配置

```python
params = dict(
    rsi_period=14,         # RSI 计算周期
    rsi_oversold=30,        # 超卖阈值
    rsi_overbought=70,      # 超买阈值
    take_profit=0.02,       # 止盈比例
    stop_loss=0.03,         # 止损比例
)

# 使用参数
def next(self, ...):
    period = self.params['rsi_period']
```

## 完整示例

```python
"""
RSI 超买超卖策略

当 RSI < 30 时做空，RSI > 70 时平仓
"""

import numpy as np
import pandas as pd
import talib


class UserStrategy:
    params = dict(
        rsi_period=14,
        rsi_oversold=30,
        rsi_overbought=70,
    )
    
    def __init__(self):
        self.order = None
        
    def next(self, get_klines_func, sell_func, close_func, position):
        # 1. 跳过未成交订单
        if self.order:
            return
        
        # 2. 获取K线数据
        df = get_klines_func(limit=50, as_df=True)
        if df is None or len(df) < self.params['rsi_period'] + 5:
            return
        
        # 3. 计算指标
        close = pd.to_numeric(df["c"], errors="coerce")
        rsi = talib.RSI(close.values, timeperiod=self.params['rsi_period'])
        rsi_val = rsi[-1] if not np.isnan(rsi[-1]) else 50.0
        
        # 4. 交易逻辑
        if position.size == 0:
            if rsi_val < self.params['rsi_oversold']:
                self.order = sell_func(size=1)
        else:
            if rsi_val > self.params['rsi_overbought']:
                self.order = close_func()
```

## 最佳实践

### 1. 数据验证

```python
df = get_klines_func(limit=100, as_df=True)
if df is None or df.empty:
    return
```

### 2. 使用 `self.order` 追踪状态

```python
def __init__(self):
    self.order = None
    self.entry_price = 0.0
```

### 3. 添加日志输出

```python
print(f"[开仓] 价格={price}, RSI={rsi:.2f}")
print(f"[平仓] 盈亏={pnl*100:.2f}%")
```

### 4. 参数注释

```python
params = dict(
    rsi_period=14,       # RSI 计算周期
    rsi_oversold=30,     # 超卖阈值
    rsi_overbought=70,   # 超买阈值
)
```

---

# 示例策略

## 运行示例

```bash
# 运行 RSI 示例
python scripts/run.py \
    --strategy examples/01_simple_rsi.py \
    --from 2025-01-01 \
    --to 2026-04-15 \
    --datasource gate

# 运行均线交叉示例
python scripts/run.py \
    --strategy examples/02_ma_cross.py \
    --market BTC_USDT \
    --interval 4h

# 指定策略参数
python scripts/run.py \
    --strategy examples/03_bollinger_bands.py \
    --strategy-params '{"bb_period": 20, "bb_std": 2.5}'
```

## 策略对比

| 策略 | 风险等级 | 适用市场 | 复杂度 |
|------|----------|----------|--------|
| RSI | 中 | 趋势 | 低 |
| MA Cross | 中 | 趋势 | 低 |
| Bollinger | 中低 | 震荡 | 中 |
| Grid | 低 | 震荡 | 中 |
| Martingale | 高 | 任何 | 中 |

### 01_simple_rsi.py - 简单 RSI 策略

最简单的 RSI 超买超卖策略：RSI < 30（超卖）时做空，RSI > 70（超买）时平仓。

**适用场景**：趋势明显的市场

### 02_ma_cross.py - 均线交叉策略

经典的双均线交叉策略：快线从上方穿越慢线（金叉）时做空，快线从下方穿越慢线（死叉）时平仓。

**适用场景**：趋势市场，过滤震荡

### 03_bollinger_bands.py - 布林带策略

基于布林带的均值回归策略：价格触及下轨时做空，价格触及中轨时平仓。

**适用场景**：震荡市场

### 04_grid_strategy.py - 网格策略

固定价格间隔的网格交易策略：在预设的价格网格上设置买卖单，价格触及网格线时自动交易。

**适用场景**：震荡市场，稳定波动

### 05_martingale.py - 马丁格尔策略

经典马丁格尔加仓策略：亏损后加倍仓位，设置止盈止损保护。

**风险警告**：高风险策略，可能造成重大损失

## 相关文档

- [根目录 README](../README.md)
- [配置参数](../configs/)
- [HTML 报告](../html/)
