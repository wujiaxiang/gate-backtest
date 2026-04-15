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
python scripts/run.py --config configs/params.json

# 自定义参数运行
python scripts/run.py \
    --market ETH_USDT \
    --interval 1d \
    --from 2025-01-01 \
    --to 2026-04-15 \
    --investment 1000 \
    --leverage 50

# 保存数据到本地
python scripts/run.py --save-data --datasource gate

# 使用本地数据
python scripts/run.py --data-file data/ETH_USDT_1d.csv

# 禁用并行回测（串行模式）
python scripts/run.py --no-parallel --market ETH_USDT

# 指定并行worker数量
python scripts/run.py --workers 4 --market ETH_USDT
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

## HTML可视化报告

运行回测后，可使用内置的HTML可视化工具查看交互式报告：

```bash
# 运行回测（自动并行优化）
python scripts/run.py \
    --datasource gate_history \
    --market ETH_USDT \
    --interval 1m \
    --from 2025-01-01 \
    --to 2026-04-15 \
    --investment 200 \
    --leverage 50

# 查看HTML报告
# 1. 直接在浏览器中打开
open html/backtest_report.html

# 2. 或者启动本地服务器（支持跨域）
cd html && python -m http.server 8080
# 访问 http://localhost:8080/backtest_report.html
```

### 查看报告

1. 打开 `html/backtest_report.html`
2. 点击页面顶部的「选择回测结果 JSON 文件」按钮
3. 选择 `results/时间戳/backtest_result.json`
4. 即可查看可视化图表

**支持拖拽**：直接将 JSON 文件拖入页面即可加载

### 报告功能特性

1. **关键指标仪表板**：总收益率、年化收益率、最大回撤、夏普比率等
2. **价格与累计收益率对照图**：ETH价格走势与累计收益双Y轴图表
3. **日收益率与收益金额图**：柱状图+折线图组合
4. **日收益率分布直方图**：展示日收益率的分布情况

### HTML报告可自定义

`html/backtest_report.html` 是纯静态文件，由用户自行迭代修改：
- 修改样式（颜色、布局等）
- 添加新图表
- 调整指标展示
- 自定义交互功能

---

## 临时文件目录说明

| 目录 | 说明 | Git忽略 |
|------|------|--------|
| `results/` | 回测结果，每次运行生成一个时间戳子目录 | ✅ |
| `data/` | K线数据缓存，从Gate下载的CSV文件 | ✅ |
| `logs/` | 运行时日志，`backtest_latest.log` | ✅ |
| `html/` | HTML可视化报告模板 | ❌ (git跟踪) |

### results/ 目录结构

```
results/
└── 20260415_120000/           # 时间戳目录
    ├── backtest_result.json   # 回测汇总数据（用于HTML报告）
    ├── equity.csv             # 每日资产数据
    ├── klines.csv             # K线数据
    ├── daily_equity.csv       # 按日汇总的资产数据
    └── backtest.log           # 完整日志
```

### HTML报告 JSON 数据规范

`backtest_result.json` 结构如下：

```json
{
  "metadata": {
    "generated_at": "2026-04-15T12:00:00",
    "version": "1.0",
    "source": "gate-backtest"
  },
  "backtest_params": {
    "market": "ETH_USDT",
    "interval": "1d",
    "backtest_from": "2025-01-01",
    "backtest_to": "2026-04-15",
    "investment": 200,
    "leverage": 50,
    "direction": "short",
    "data_source": "gate_history",
    "commission": 0.0005
  },
  "key_metrics": {
    "total_return_pct": 148.28,
    "annual_return_pct": 57.57,
    "max_drawdown_pct": 65.16,
    "sharpe_ratio": 10.42,
    "volatility_pct": 56.75,
    "win_rate_pct": 57.53,
    "initial_price": 1191.00,
    "final_price": 2957.00
  },
  "data_series": {
    "equity": [
      {"time": "2025-01-01T00:00:00", "price": 1191.0, "fund": 200.0, "position_size": 0},
      {"time": "2025-01-02T00:00:00", "price": 1210.5, "fund": 198.5, "position_size": -0.5},
      ...
    ],
    "trades": [
      {"entry_time": "...", "exit_time": "...", "pnl": 0.015, ...}
    ],
    "sample_size": 1096
  },
  "performance_summary": {
    "total_days": 470,
    "data_points": 1096,
    "execution_time": 120
  }
}
```

### JSON 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `backtest_params` | object | 回测参数配置 |
| `key_metrics` | object | 关键指标 |
| `key_metrics.total_return_pct` | float | 总收益率(%) |
| `key_metrics.annual_return_pct` | float | 年化收益率(%) |
| `key_metrics.max_drawdown_pct` | float | 最大回撤(%) |
| `key_metrics.sharpe_ratio` | float | 夏普比率 |
| `key_metrics.volatility_pct` | float | 波动率(%) |
| `key_metrics.win_rate_pct` | float | 胜率(%) |
| `key_metrics.initial_price` | float | 初始价格 |
| `key_metrics.final_price` | float | 最终价格 |
| `data_series.equity` | array | 每日资产序列 |
| `data_series.equity[].time` | string | 时间戳 |
| `data_series.equity[].price` | float | ETH价格 |
| `data_series.equity[].fund` | float | 账户资金 |
| `data_series.equity[].position_size` | float | 持仓数量(负=做空) |

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
│   ├── run.py               # 主入口 (合并版，支持并行)
│   └── export_results.py    # CSV转JSON导出工具
├── html/                    # HTML可视化报告（用户可自定义）
│   └── backtest_report.html # 报告模板
├── examples/                # 策略示例 ⭐
│   ├── 01_simple_rsi.py     # 简单 RSI 策略
│   ├── 02_ma_cross.py       # 均线交叉策略
│   ├── 03_bollinger_bands.py # 布林带策略
│   ├── 04_grid_strategy.py   # 网格策略
│   └── 05_martingale.py     # 马丁格尔策略
├── docs/                    # 文档
│   └── USER_STRATEGY_TUTORIAL.md  # 策略编写教程 ⭐
├── configs/                 # 配置文件
├── data/                    # K线数据缓存（git忽略）
├── results/                 # 回测结果（git忽略）
├── logs/                    # 运行时日志（git忽略）
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

| 交易所 | 代码 | 类型 | 说明 |
|--------|------|------|------|
| Gate.io | `gate` | 永续合约 | ccxt 实时拉取 (有 API 限制) |
| Gate.io 历史 | `gate_history` | 批量历史数据 | download.gatedata.org 批量下载 |
| 币安 | `binance` | 现货/合约 | ccxt 实时拉取 |
| OKX | `okx` | 永续合约 | ccxt 实时拉取 |
| Hyperliquid | `hyperliquid` | 永续合约 | ccxt 实时拉取 |

### Gate.io 历史批量数据 (推荐)

Gate.io 提供完整的历史K线批量下载服务，覆盖从 **2023年1月起** 的所有历史数据:

```bash
# backtrader 版本
python scripts/run_backtest.py \
    --exchange gate_history \
    --symbol ETH/USDT \
    --interval 1d \
    --from 2023-01-01 \
    --to 2025-12-31 \
    --save-data

# 轻量版
python scripts/backtest.py \
    --datasource gate_history \
    --market ETH_USDT \
    --interval 1d \
    --from 2023-01-01 \
    --to 2025-12-31
```

**支持的数据类型:**

| biz 参数 | 含义 | 数据来源 |
|---------|------|---------|
| `spot` | 现货 & 杠杆 | download.gatedata.org/spot/ |
| `futures_usdt` (默认) | USDT 本位合约 | download.gatedata.org/futures_usdt/ |
| `futures_btc` | BTC 本位合约 | download.gatedata.org/futures_btc/ |

**支持的时间周期:** `1m`, `5m`, `1h`, `4h`, `1d`, `7d`

**数据格式:**
```csv
timestamp,o,h,l,c,v
2023-01-01 00:00:00+00:00,1550.5,1560.2,1548.3,1555.8,12345.67
...
```

**本地文件加载:** 下载后的 `.csv.gz` 文件可直接使用:
```bash
python scripts/run_backtest.py --data-file data/gate_history/futures_usdt/candlesticks_1d/202301/ETH_USDT-202301.csv.gz
```

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

## 开发规范

### 核心原则

1. **插件接口规范不可修改**
   - `UserStrategy` 类的 `__init__`、`next` 方法签名和参数约定为公开接口
   - 策略调用方式（如 `get_klines_func`、`sell_func`、`close_func`）为稳定契约
   - 如需扩展功能，应在框架层实现，插件层无感知

2. **框架修改必须通过单元测试验证**
   - 每次修改 `scripts/backtest.py` 或 `runner/` 下的框架代码后
   - 必须运行 `unittest/` 目录下的单元测试确保功能正常
   - 测试通过后方可进行全量回测

### 测试流程

```bash
# 1. 修改框架代码后，运行单元测试
cd gate-backtest
python -m pytest unittest/ -v

# 2. 确认测试全部通过后，再进行全量回测
python scripts/backtest.py --datasource gate_history ...
```

### 性能优化原则

- **预计算优先**: 技术指标（RSI、ATR等）在回测开始前一次性计算
- **代理模式**: 使用 `TalibProxy` 拦截talib调用，策略代码无需修改
- **向量化计算**: 优先使用pandas/numpy批量计算，避免逐行循环

### 单元测试结构

```
unittest/
├── helpers.py       # 测试辅助函数和数据生成
├── test_engine.py   # 引擎核心功能测试
├── test_export.py   # 数据导出功能测试
└── test_data/       # 测试用小数据集
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
