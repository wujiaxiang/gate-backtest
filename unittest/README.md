# 单元测试说明

本目录包含回测框架的单元测试代码。

## 目录结构

```
unittest/
├── README.md              # 本文档
├── helpers.py             # 测试辅助函数和数据生成
├── test_engine.py         # 引擎核心功能测试
├── test_export.py         # 数据导出功能测试
└── test_data/             # 测试用小数据集
    └── sample_klines.csv  # 示例K线数据
```

## 运行测试

### 基本命令

```bash
# 运行所有测试
python -m pytest unittest/ -v

# 运行指定测试文件
python -m pytest unittest/test_engine.py -v

# 运行指定测试用例
python -m pytest unittest/test_engine.py::TestBacktestEngine::test_basic_backtest -v
```

### 使用 pytest

```bash
# 详细输出
python -m pytest unittest/ -v --tb=short

# 显示 print 输出
python -m pytest unittest/ -v -s

# 失败时停止
python -m pytest unittest/ -v -x

# 生成覆盖率报告
python -m pytest unittest/ --cov=gate_backtest --cov-report=term-missing
```

## 测试说明

### test_engine.py - 引擎测试

测试回测引擎的核心功能：

| 测试用例 | 说明 |
|----------|------|
| `test_basic_backtest` | 基本回测流程 |
| `test_position_management` | 仓位管理 |
| `test_order_execution` | 订单执行 |
| `test_pnl_calculation` | 盈亏计算 |
| `test_stop_loss` | 止损逻辑 |
| `test_take_profit` | 止盈逻辑 |

### test_export.py - 导出测试

测试数据导出功能：

| 测试用例 | 说明 |
|----------|------|
| `test_export_json` | JSON 导出 |
| `test_export_csv` | CSV 导出 |
| `test_export_equity` | 权益数据导出 |
| `test_export_trades` | 交易记录导出 |

### helpers.py - 测试辅助

提供测试所需的辅助函数：

```python
from unittest.helpers import generate_sample_data, create_test_engine

# 生成测试数据
klines = generate_sample_data(days=30)

# 创建测试引擎
engine = create_test_engine(
    strategy_class=TestStrategy,
    initial_cash=1000
)
```

## 测试规范

### 命名规范

- 测试文件：`test_*.py`
- 测试类：`Test*`
- 测试函数：`test_*`

### 测试结构

```python
import pytest
from gate_backtest import BacktestEngine

class TestBacktestEngine:
    """回测引擎测试"""
    
    def test_basic_backtest(self):
        """基本回测流程测试"""
        # Arrange
        engine = BacktestEngine(initial_cash=1000)
        data = generate_sample_data()
        
        # Act
        result = engine.run(data)
        
        # Assert
        assert result is not None
        assert result.total_return >= 0
```

### 测试原则

1. **独立性**：每个测试用例独立运行，不依赖其他测试
2. **可重复性**：测试结果稳定，可重复执行
3. **快速执行**：单个测试用例执行时间 < 1 秒
4. **明确断言**：每个测试有明确的断言，验证预期结果

## 开发流程

### 修改代码后必须运行测试

```
修改框架代码
    │
    ▼
运行单元测试 ────► 失败？───► 修复代码
    │
    ▼
全部通过？
    │
    ▼
进行全量回测
```

### 测试覆盖范围

- ✅ 引擎核心逻辑
- ✅ 数据导出功能
- ✅ 订单执行
- ✅ 仓位管理
- ⚠️ 策略逻辑（建议在 examples/ 中手动测试）

## 常见问题

### Q: 测试失败怎么办？

1. 检查测试数据是否正确
2. 查看详细的错误信息：`pytest -v --tb=long`
3. 单独运行失败的测试：`pytest -v -x file.py::test_name`

### Q: 如何添加新测试？

```python
def test_new_feature(self):
    """新功能测试"""
    # 准备测试数据
    data = generate_sample_data(days=100)
    
    # 执行待测功能
    engine = BacktestEngine(initial_cash=1000)
    result = engine.run(data)
    
    # 验证结果
    assert result.metrics.total_return > 0
```

### Q: 测试数据从哪里来？

使用 `helpers.py` 中的数据生成函数：

```python
from unittest.helpers import generate_sample_data

# 生成 30 天的测试数据
data = generate_sample_data(days=30)

# 生成指定价格范围的数据
data = generate_sample_data(
    days=30,
    initial_price=1000,
    volatility=0.02
)
```

## 相关文档

- [根目录 README](../README.md)
- [引擎架构说明](../runner/)
- [策略示例 + 教程](../examples/)
