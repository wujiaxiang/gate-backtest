# Gate-Backtest

基于 Backtrader 的加密货币回测框架

## 架构

```
gate-backtest/
├── backtest_runner.py              # 主入口脚本 (推荐)
├── runner/
│   ├── adapters/
│   │   ├── backtrader_adapter.py   # Backtrader 适配器 (引擎层)
│   │   └── gate_adapter.py         # Gate 风格适配器
│   ├── backtest/
│   │   └── engine.py               # 回测引擎
│   ├── data/
│   │   ├── fetcher.py              # 通用数据获取器
│   │   ├── realtime_fetcher.py     # CCXT 实时数据获取
│   │   └── gate_histor.py          # Gate.io 历史数据下载
│   └── strategies/
│       └── user_strategy.py         # 用户策略基类 (Gate 风格)
├── strategy_wrapper.py              # 马丁格尔策略包装器
├── configs/
│   └── params.json                  # 参数配置
└── results/                         # 回测结果输出目录
```

## 核心设计

### 1. 数据层 (`runner/data/`)

| 模块 | 功能 |
|------|------|
| `fetcher.py` | 通用数据获取接口 |
| `realtime_fetcher.py` | CCXT 统一接口，支持多交易所秒级/分钟级数据 |
| `gate_histor.py` | Gate.io 历史批量数据下载 |

**CCXT 支持的交易所**: Binance, Gate.io, Bybit, OKX, KuCoin, Bitget, Mexc

### 2. 适配器层 (`runner/adapters/`)

Backtrader 适配器负责：
- 数据格式转换
- 订单撮合
- 保证金/杠杆计算
- 分析器配置

### 3. 策略层

策略使用 **Gate.io 风格接口**：

```python
def next_gate(self, get_klines_func, sell_func, close_func, position):
    """
    Args:
        get_klines_func: 获取K线数据的函数
        sell_func: 开仓函数
        close_func: 平仓函数
        position: 当前持仓对象
    """
    df = get_klines_func(limit=50, as_df=True)

    if position.size == 0:
        # 开仓
        self.order = sell_func()
    else:
        # 平仓
        self.order = close_func()
```

## 使用方法

### 主入口 (推荐)

```bash
# ==================== 数据源 ====================

# 本地文件回测
python backtest_runner.py --csv ./ETH.csv.gz --cash 10000 --leverage 50

# 在线获取数据回测 (CCXT)
python backtest_runner.py --symbol ETH/USDT --exchange gateio --interval 1m --hours 24
python backtest_runner.py --symbol BTC/USDT --exchange gateio --interval 1s --hours 2

# 秒级数据自动调整参数
python backtest_runner.py --symbol ETH/USDT --exchange gateio --interval 1s --hours 1 --second_mode

# ==================== 完整参数 ====================

python backtest_runner.py \
    --symbol ETH/USDT \
    --exchange gateio \
    --interval 1m \
    --hours 24 \
    --params configs/params.json \
    --cash 10000 \
    --leverage 50 \
    --commission 0.0002 \
    --export_dir results \
    --export_html
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--csv` | 本地 CSV/GZ 文件路径 | - |
| `--symbol` | 交易对 (CCXT格式: BTC/USDT) | - |
| `--exchange` | 交易所 | gateio |
| `--interval` | 时间间隔 (1s, 1m, 5m, 1h) | 1m |
| `--hours` | 获取多少小时数据 | 24 |
| `--params` | 参数 JSON 文件 | - |
| `--cash` | 初始资金 | 10000 |
| `--leverage` | 杠杆倍数 | 50 |
| `--commission` | 手续费率 | 0.0002 |
| `--second_mode` | 秒级数据模式 (自动调整参数) | False |
| `--from` / `--to` | 日期过滤 (本地文件) | - |
| `--export_html` | 导出 HTML 友好的结构化数据 | - |

### 代码调用

```python
from runner.backtest import backtest
from runner.strategies import UserStrategy
import pandas as pd

# 加载数据
df = pd.read_csv('data/klines.csv')

# 一行代码回测
engine = backtest(
    df=df,
    strategy_class=UserStrategy,
    cash=200,
    leverage=50,
    investment=200,
    direction='short',
    take_profit=0.25,
    stop_loss=0.25,
)

print(engine.summary())
```

## 策略接口

策略继承 `UserStrategy`，只需实现 `next_gate` 方法：

```python
class MyStrategy(UserStrategy):
    params = dict(
        period=20,
        stop_loss=0.1,
        take_profit=0.2,
    )

    def next_gate(self, get_klines_func, sell_func, close_func, position):
        df = get_klines_func(limit=50, as_df=True)

        if df.empty:
            return

        price = df['close'].iloc[-1]

        if position.size == 0:
            # 开仓逻辑
            if self.should_open():
                self.order = sell_func()
        else:
            # 平仓逻辑
            if self.should_close():
                self.order = close_func()
```

## 回测结果字段

| 字段 | 说明 |
|------|------|
| `initial_cash` | 初始资金 |
| `final_value` | 最终权益 |
| `profit` | 收益金额 |
| `roi_pct` | 总收益率 (%) |
| `sharpe` | 夏普比率 |
| `max_drawdown` | 最大回撤 (%) |
| `sqn` | 系统质量数 |
| `total_trades` | 总交易次数 |
| `win_count` | 盈利交易数 |
| `loss_count` | 亏损交易数 |
| `win_rate_pct` | 胜率 (%) |
| `profit_factor` | 盈亏比 |
| `equity_curve` | 权益曲线数据 |

## HTML 报告数据

使用 `--export_html` 参数导出结构化报告数据：

```bash
python backtest_runner.py --symbol ETH/USDT --exchange gateio --export_html
```

生成 `results/时间戳/report.json`，包含：

```json
{
  "metadata": {
    "generated_at": "2026-04-16T01:31:00",
    "source": "gate-backtest"
  },
  "backtest_params": {
    "market": "ETH_USDT",
    "interval": "1m",
    "leverage": 50
  },
  "key_metrics": {
    "total_return_pct": 0.34,
    "sharpe_ratio": 1.23,
    "max_drawdown_pct": 5.2,
    "win_rate_pct": 60.0,
    "profit_factor": 1.5,
    "sqn": 2.1,
    "total_trades": 5,
    "win_count": 3,
    "loss_count": 2
  },
  "data_series": {
    "equity": [{"time": "...", "price": 2500, "fund": 10034}],
    "daily_returns": [0.12, -0.05, ...],
    "cumulative_returns": [0.12, 0.07, ...],
    "dates": ["2026-04-16", ...]
  },
  "chart_data": {
    "price_equity": [...],
    "return_distribution": [{"range": "0~1%", "count": 10}, ...]
  }
}
```

可直接绑定到 Chart.js、ECharts 等图表库生成 HTML 报告。

## 安装

```bash
pip install backtrader pandas numpy requests talib ccxt
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `backtest_runner.py` | **主入口脚本** (推荐使用) |
| `strategy_wrapper.py` | 马丁格尔策略包装器 |
| `runner/adapters/backtrader_adapter.py` | Backtrader 适配器 |
| `runner/adapters/gate_adapter.py` | Gate 风格适配器 |
| `runner/backtest/engine.py` | 回测引擎 |
| `runner/data/realtime_fetcher.py` | CCXT 数据获取器 |
| `runner/strategies/user_strategy.py` | 用户策略基类 |

## 数据格式

### 本地数据

支持 CSV 和 GZ 压缩格式：

```
# CSV: datetime,open,high,low,close,volume
2026-01-01 00:00:00,2400.5,2410.0,2390.0,2405.0,15000

# GZ: timestamp,volume,open,high,low,close (Gate.io 格式)
1704067200,15000,2400.5,2410.0,2390.0,2405.0
```

### 数据目录结构

```
data/
└── gate_history/
    └── futures_usdt/
        ├── candlesticks_1m/YYYYMM/SYMBOL-YYYYMM.csv.gz
        ├── candlesticks_5m/YYYYMM/SYMBOL-YYYYMM.csv.gz
        ├── candlesticks_1h/YYYYMM/SYMBOL-YYYYMM.csv.gz
        └── candlesticks_1d/YYYYMM/SYMBOL-YYYYMM.csv.gz
```

## 马丁格尔策略参数

```json
{
    "leverage": 50,
    "take_profit": 0.25,
    "stop_loss": 0.25,
    "ladder_threshold_0": 0.0,
    "ladder_threshold_1": 0.7,
    "ladder_threshold_2": 0.9,
    "ladder_threshold_3": 1.1,
    "ladder_mult_0": 1,
    "ladder_mult_1": 2,
    "ladder_mult_2": 4,
    "ladder_mult_3": 8,
    "coef_min": 1.0,
    "coef_max": 2.0,
    "tp_min": 0.005,
    "tp_max": 0.02,
    "rsi_period": 14,
    "atr_period": 14,
    "compounding_ratio": 0.3
}
```

### 秒级数据参数 (使用 --second_mode)

秒级数据波动极小 (平均 0.0035%)，需要调整参数：

```json
{
    "take_profit": 0.001,
    "stop_loss": 0.001,
    "ladder_threshold_1": 0.02,
    "ladder_threshold_2": 0.04,
    "coef_min": 0.3,
    "coef_max": 0.8,
    "rsi_period": 7,
    "atr_period": 7
}
```
