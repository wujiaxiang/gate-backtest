# Gate-Backtest

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> Gate.io 量化策略本地回测框架，基于 backtrader + ccxt 构建

## 特性

- **多交易所支持**: Gate.io、币安、OKX、Hyperliquid
- **Gate.io 风格策略**: 兼容 Gate.io 量化策略代码规范
- **真实数据回测**: 通过 ccxt 获取历史K线数据
- **完整分析报告**: 收益率、夏普比率、最大回撤、胜率等指标
- **并行回测**: 多进程加速，大幅缩短回测时间

## 安装

```bash
# 克隆项目
git clone https://github.com/yourname/gate-backtest.git
cd gate-backtest

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 安装 TA-Lib (可选)
brew install ta-lib  # Mac
pip install TA-Lib
```

## 快速开始

### 一行命令回测

```bash
# 使用默认配置运行
python scripts/run.py --config configs/params.json

# 自定义参数运行
python scripts/run.py \
    --market ETH_USDT \
    --interval 1d \
    --from 2025-01-01 \
    --to 2026-04-15 \
    --investment 200 \
    --leverage 50
```

### 查看 HTML 报告

```bash
# 运行回测后，打开报告
open html/backtest_report.html

# 或启动本地服务器
cd html && python -m http.server 8080
```

1. 点击「选择回测结果 JSON 文件」
2. 选择 `results/时间戳/backtest_result.json`
3. 查看可视化图表

### Python API

```python
from gate_backtest import BacktestEngine

engine = BacktestEngine(
    strategy_class=UserStrategy,
    initial_cash=1000,
    commission=0.0005
)
result = engine.run(data)
engine.print_report(result)
```

## 文档导航

| 模块 | 说明 |
|------|------|
| [examples/](examples/) | **策略示例 + 编写教程** - 示例代码 + 从零开发策略 |
| [html/](html/) | [HTML 报告](html/) - 可视化报告使用与自定义 |
| [scripts/](scripts/) | [脚本使用](scripts/) - 命令行参数详解 |
| [configs/](configs/) | [配置参数](configs/) - 参数配置说明 |
| [runner/](runner/) | [引擎架构](runner/) - 框架核心模块说明 |
| [unittest/](unittest/) | [单元测试](unittest/) - 测试说明与规范 |

## 项目结构

```
gate-backtest/
├── examples/                # 策略示例 + 编写教程
├── html/                    # HTML 可视化报告（用户可自定义）
├── scripts/                 # 回测脚本
│   └── run.py               # 主入口（支持并行）
├── configs/                  # 参数配置
├── runner/                   # 核心引擎
├── unittest/                 # 单元测试
├── data/                    # K线缓存（git忽略）
├── results/                 # 回测结果（git忽略）
├── logs/                    # 运行时日志（git忽略）
└── README.md                # 本文档
```

## 临时文件

| 目录 | 说明 | Git 忽略 |
|------|------|----------|
| `data/` | K线数据缓存 | ✅ |
| `results/` | 回测结果 | ✅ |
| `logs/` | 运行时日志 | ✅ |
| `html/` | 报告模板 | ❌ |

## 风险提示

⚠️ **重要**:

1. 高杠杆交易风险极高，可能导致本金全部损失
2. 回测结果基于历史数据，不保证未来表现
3. 请在模拟环境充分测试后再考虑实盘交易

## 许可证

MIT License - 详见 [LICENSE](LICENSE)
