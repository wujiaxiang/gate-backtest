# Gate-Backtest

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> Gate.io 量化策略本地回测框架，基于 backtrader + ccxt 构建

## 特性

- **多交易所支持**: Gate.io、币安、OKX、Hyperliquid
- **Gate.io 风格策略**: 兼容 Gate.io 量化策略代码规范
- **真实数据回测**: 通过 ccxt 获取历史K线数据
- **完整分析报告**: 收益率、夏普比率、最大回撤、胜率等指标

## 安装

```bash
# 克隆项目
git clone https://github.com/yourname/gate-backtest.git
cd gate-backtest

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装 TA-Lib (可选，技术指标)
# Linux/Mac:
brew install ta-lib  # Mac
# sudo apt-get install ta-lib  # Ubuntu
pip install TA-Lib
```

## 快速开始

### 命令行运行

```bash
# 使用默认配置运行
python scripts/run_backtest.py --config configs/params.json

# 自定义参数运行
python scripts/run_backtest.py \
    --symbol ETH/USDT \
    --interval 1d \
    --from 2025-01-01 \
    --to 2026-04-15 \
    --investment 1000 \
    --leverage 50

# 保存数据到本地
python scripts/run_backtest.py --save-data --exchange gate

# 使用本地数据
python scripts/run_backtest.py --data-file data/ETH_USDT_1d.csv

# 生成回测图表
python scripts/run_backtest.py --plot
```

### Python API

```python
from gate_backtest import BacktestEngine, UserStrategy
from gate_backtest.data import DataFetcher

# 获取数据
fetcher = DataFetcher('gate')
data = fetcher.fetch_ohlcv(
    symbol='ETH/USDT',
    interval='1d',
    start_date='2025-01-01',
    end_date='2026-04-15'
)

# 创建引擎
engine = BacktestEngine(
    strategy_class=UserStrategy,
    initial_cash=1000,
    commission=0.0005
)

# 运行回测
result = engine.run(data)

# 打印报告
engine.print_report(result)
```

## 项目结构

```
gate-backtest/
├── runner/                  # 主包 (backtrader 版本)
│   ├── adapters/            # 适配器模块
│   ├── data/                # 数据获取
│   ├── strategies/          # 策略模块
│   ├── backtest/            # 回测引擎
│   └── utils/               # 工具函数
├── scripts/                 # 回测脚本
│   ├── backtest.py          # 轻量版 (Gate 官方风格)
│   └── run_backtest.py      # backtrader 版本
├── examples/                # 策略示例 ⭐
│   ├── 01_simple_rsi.py     # 简单 RSI 策略
│   ├── 02_ma_cross.py       # 均线交叉策略
│   ├── 03_bollinger_bands.py # 布林带策略
│   ├── 04_grid_strategy.py   # 网格策略
│   └── 05_martingale.py     # 马丁格尔策略
├── docs/                    # 文档
│   └── USER_STRATEGY_TUTORIAL.md  # 策略编写教程 ⭐
├── configs/                 # 配置文件
├── requirements.txt
└── README.md
```

## 策略参数

在 `configs/params.json` 中配置:

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `market` | 交易对 | ETH_USDT |
| `interval` | K线周期 | 1d |
| `investment` | 初始投资 | 200 USDT |
| `leverage` | 杠杆倍数 | 50 |
| `commission` | 手续费率 | 0.0002 |
| `take_profit` | 止盈比例 | 0.25 |
| `stop_loss` | 止损比例 | 0.25 |

### 马丁格尔阶梯

```json
{
  "ladder_threshold_1": 0.7,
  "ladder_mult_1": 2,
  "ladder_threshold_2": 0.9,
  "ladder_mult_2": 4
  // ... 更多阶梯
}
```

## 内置策略: 马丁格尔加仓策略

### 核心特性

- **马丁格尔加仓**: 基于亏损比例的多阶梯加仓
- **动态止盈止损**: 根据市场波动调整阈值
- **利润复投**: 30%盈利自动滚入投资本金
- **动态参数**: 基于RSI和ATR调整策略参数

### 策略逻辑

1. **开仓**: 做空入场，计算基础仓位
2. **止盈**: 根据阶梯和动态系数计算止盈阈值
3. **止损**: 固定止损比例止损
4. **加仓**: 亏损达到阈值时，马丁格尔加仓
5. **复投**: 盈利的30%加入投资本金

## 编写自己的策略 ⭐

查看 [策略编写教程](docs/USER_STRATEGY_TUTORIAL.md) 学习如何开发新策略。

### 快速示例

```python
import talib

class UserStrategy:
    params = dict(rsi_period=14)
    
    def __init__(self):
        self.order = None
        
    def next(self, get_klines_func, sell_func, close_func, position):
        if self.order:
            return
        
        df = get_klines_func(limit=50, as_df=True)
        rsi = talib.RSI(df["c"].values, timeperiod=14)
        
        if position.size == 0 and rsi[-1] < 30:
            self.order = sell_func(size=1)
        elif position.size > 0 and rsi[-1] > 70:
            self.order = close_func()
```

### 运行示例策略

```bash
# 运行 RSI 示例
python3 scripts/backtest.py \
    --strategy examples/01_simple_rsi.py \
    --from 2025-01-01 \
    --to 2026-04-15 \
    --datasource gate
```

更多示例见 [examples/](examples/) 目录。

## 交易所支持

| 交易所 | 代码 | 类型 |
|--------|------|------|
| Gate.io | `gate` | 永续合约 |
| 币安 | `binance` | 现货/合约 |
| OKX | `okx` | 永续合约 |
| Hyperliquid | `hyperliquid` | 永续合约 |

## 开发

```bash
# 运行测试
pytest tests/

# 代码格式化
black gate_backtest/

# 类型检查
mypy gate_backtest/

# 代码检查
flake8 gate_backtest/
```

## 风险提示

⚠️ **重要**:

1. 马丁格尔策略可能在高波动市场造成重大损失
2. 高杠杆交易风险极高，可能导致本金全部损失
3. 回测结果基于历史数据，不保证未来表现
4. 请在模拟环境充分测试后再考虑实盘交易

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 贡献

欢迎提交 Issue 和 Pull Request!
