# UserStrategy 编写教程

本教程教你如何编写 Gate.io 量化策略。

## 目录

1. [基础结构](#1-基础结构)
2. [核心方法](#2-核心方法)
3. [参数配置](#3-参数配置)
4. [数据获取](#4-数据获取)
5. [交易操作](#5-交易操作)
6. [完整示例](#6-完整示例)
7. [最佳实践](#7-最佳实践)

---

## 1. 基础结构

每个策略文件都需要包含一个 `UserStrategy` 类：

```python
import numpy as np
import pandas as pd
import talib


class UserStrategy:
    """策略描述"""
    
    # 策略参数
    params = dict(
        param1=10,
        param2=20,
    )
    
    def __init__(self):
        """初始化"""
        self.order = None
        
    def next(self, get_klines_func, sell_func, close_func, position):
        """策略主逻辑"""
        pass
```

---

## 2. 核心方法

### `next(get_klines_func, sell_func, close_func, position)`

每根 K 线触发一次，是策略的核心逻辑。

**参数说明：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `get_klines_func` | function | 获取K线数据的函数 |
| `sell_func` | function | 开仓函数 |
| `close_func` | function | 平仓函数 |
| `position` | object | 持仓对象，包含 `.size` 属性 |

---

## 3. 参数配置

在 `params` 字典中定义可调参数：

```python
params = dict(
    # 基础参数
    leverage=10,
    investment=1000,
    
    # 技术指标参数
    rsi_period=14,
    rsi_oversold=30,
    rsi_overbought=70,
    
    # 止盈止损
    take_profit=0.02,
    stop_loss=0.03,
)
```

**参数使用：**

```python
def next(self, ...):
    rsi_period = self.params['rsi_period']  # 获取参数
```

---

## 4. 数据获取

### 获取K线数据

```python
def next(self, get_klines_func, ...):
    # 获取最近100根K线
    df = get_klines_func(limit=100, as_df=True)
    
    if df is None or df.empty:
        return
    
    # 数据列名: o(open), h(high), l(low), c(close), v(volume)
    close = df["c"]
    high = df["h"]
    low = df["l"]
```

### 计算技术指标

使用 `talib` 计算指标：

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

---

## 5. 交易操作

### 开仓

```python
def next(self, get_klines_func, sell_func, close_func, position):
    if position.size == 0:  # 无持仓
        # 开多仓
        self.order = sell_func(size=1.0)
```

### 平仓

```python
def next(self, ...):
    if position.size > 0:  # 有持仓
        self.order = close_func()
```

### 订单状态

使用 `self.order` 追踪订单：

```python
def __init__(self):
    self.order = None  # 初始无订单

def next(self, ...):
    if self.order:
        return  # 订单未成交，跳过
    
    # ... 下单逻辑
    self.order = sell_func(size=1.0)
```

---

## 6. 完整示例

```python
"""
RSI 策略示例
"""

import numpy as np
import pandas as pd
import talib


class UserStrategy:
    """
    RSI 超买超卖策略
    
    当 RSI < 30 时买入，RSI > 70 时卖出
    """
    
    params = dict(
        rsi_period=14,
        rsi_oversold=30,
        rsi_overbought=70,
    )
    
    def __init__(self):
        self.order = None
        
    def next(self, get_klines_func, sell_func, close_func, position):
        """策略主逻辑"""
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
            # 无持仓，RSI 超卖时买入
            if rsi_val < self.params['rsi_oversold']:
                self.order = sell_func(size=1)
        else:
            # 有持仓，RSI 超买时卖出
            if rsi_val > self.params['rsi_overbought']:
                self.order = close_func()
```

---

## 7. 最佳实践

### 1. 数据验证

```python
df = get_klines_func(limit=100, as_df=True)
if df is None or df.empty:
    return

# 检查必要列
if "c" not in df.columns:
    return
```

### 2. 避免重复下单

```python
def __init__(self):
    self.order = None

def next(self, ...):
    if self.order:  # 已有订单
        return
```

### 3. 使用 `self.order` 追踪状态

```python
def __init__(self):
    self.order = None
    self.entry_price = 0.0
    self.position_size = 0.0
```

### 4. 添加日志输出

```python
print(f"[开仓] 价格={price}, RSI={rsi:.2f}")
print(f"[平仓] 盈亏={pnl*100:.2f}%")
```

### 5. 参数注释

```python
params = dict(
    rsi_period=14,       # RSI 计算周期
    rsi_oversold=30,     # 超卖阈值
    rsi_overbought=70,   # 超买阈值
)
```

---

## 常见问题

### Q: 如何处理停机/节假日数据？

```python
# 检查时间间隔是否正常
times = pd.to_datetime(df['time'])
if len(times) > 1:
    interval = (times.iloc[-1] - times.iloc[-2]).total_seconds()
    if interval > 86400:  # 超过1天
        # 跳过或处理
        pass
```

### Q: 如何实现复杂条件？

```python
# 多条件组合
if condition1 and condition2:
    # 做多
    pass

# 使用标志位
if not hasattr(self, 'last_signal'):
    self.last_signal = None

if current_signal != self.last_signal:
    # 信号变化
    pass
```

---

## 下一步

- 查看 [examples](../examples/) 目录下的示例策略
- 学习如何配置 [params.json](../configs/params.json)
- 使用本地回测脚本测试你的策略
