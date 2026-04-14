# 策略示例

这里提供多个从简单到复杂的策略示例，帮助你快速上手。

## 示例列表

| 文件 | 难度 | 描述 |
|------|------|------|
| [01_simple_rsi.py](01_simple_rsi.py) | ⭐ | 简单 RSI 策略，最基础的入门示例 |
| [02_ma_cross.py](02_ma_cross.py) | ⭐⭐ | 均线交叉策略，展示多指标组合 |
| [03_bollinger_bands.py](03_bollinger_bands.py) | ⭐⭐ | 布林带策略 |
| [04_grid_strategy.py](04_grid_strategy.py) | ⭐⭐ | 网格策略，展示网格交易思想 |
| [05_martingale.py](05_martingale.py) | ⭐⭐⭐ | 马丁格尔策略，进阶示例 |

## 运行示例

```bash
# 使用轻量版回测
cd gate-backtest
python3 scripts/backtest.py \
    --strategy examples/01_simple_rsi.py \
    --from 2025-01-01 \
    --to 2026-04-15 \
    --datasource gate

# 使用 backtrader 版本
python3 scripts/run_backtest.py \
    --strategy examples/01_simple_rsi.py \
    --from 2025-01-01 \
    --to 2026-04-15
```

## 学习路径

1. **入门**: 从 `01_simple_rsi.py` 开始，理解策略基本结构
2. **进阶**: 查看 `02_ma_cross.py`，学习多指标组合
3. **实战**: 参考 `05_martingale.py`，实现完整的交易策略

## 创建新策略

```python
"""
策略名称
--------
描述
"""

import numpy as np
import pandas as pd
import talib


class UserStrategy:
    """策略描述"""
    
    params = dict(
        # 参数定义
    )
    
    def __init__(self):
        self.order = None
        
    def next(self, get_klines_func, sell_func, close_func, position):
        # 你的策略逻辑
        pass
```

详细教程请查看 [docs/USER_STRATEGY_TUTORIAL.md](../docs/USER_STRATEGY_TUTORIAL.md)
