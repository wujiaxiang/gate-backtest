# 配置参数说明

本目录包含回测框架的配置文件。

## 目录结构

```
configs/
├── README.md              # 本文档
└── params.json           # 默认参数配置
```

## params.json

默认配置文件，定义回测的基本参数。

### 参数说明

#### 市场参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `market` | string | 交易对 | `ETH_USDT` |
| `interval` | string | K线周期 | `1d` |

**支持的交易对**：`ETH_USDT`, `BTC_USDT`, `SOL_USDT` 等主流交易对

**支持的周期**：`1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `7d`

#### 回测参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `investment` | number | 初始投资金额 (USDT) | `200` |
| `leverage` | number | 杠杆倍数 | `50` |
| `commission` | number | 手续费率 | `0.0005` |
| `direction` | string | 交易方向 | `short` |

**direction 可选值**：

- `short`：做空（卖出开空）
- `long`：做多（买入开多）
- `both`：双向（做多做空）

#### 数据源参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `data_source` | string | 数据源类型 | `gate_history` |
| `backtest_from` | string | 回测起始日期 | `2025-01-01` |
| `backtest_to` | string | 回测结束日期 | `2026-04-15` |

**data_source 可选值**：

| 值 | 说明 |
|----|------|
| `gate` | Gate.io 实时（ccxt） |
| `gate_history` | Gate.io 历史批量数据（推荐） |
| `binance` | 币安（ccxt） |
| `okx` | OKX（ccxt） |
| `hyperliquid` | Hyperliquid（ccxt） |

#### 风控参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `stop_loss` | number | 止损比例 | `0.25` |
| `take_profit` | number | 止盈比例 | `0.25` |
| `max_position` | number | 最大持仓数量 | `10` |

#### 马丁格尔阶梯参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `ladder_threshold_1` | number | 第一阶梯阈值 | `0.7` |
| `ladder_mult_1` | number | 第一阶梯倍数 | `2` |
| `ladder_threshold_2` | number | 第二阶梯阈值 | `0.9` |
| `ladder_mult_2` | number | 第二阶梯倍数 | `4` |
| `ladder_threshold_3` | number | 第三阶梯阈值 | `1.1` |
| `ladder_mult_3` | number | 第三阶梯倍数 | `8` |

**阶梯说明**：当亏损达到阶梯阈值时，仓位按对应倍数增加。

#### 策略参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `strategy_path` | string | 策略文件路径 | 无 |
| `strategy_params` | object | 策略自定义参数 | `{}` |

## 完整配置示例

```json
{
  "market": "ETH_USDT",
  "interval": "1d",
  "backtest_from": "2025-01-01",
  "backtest_to": "2026-04-15",
  "investment": 200,
  "leverage": 50,
  "commission": 0.0005,
  "direction": "short",
  "data_source": "gate_history",
  
  "stop_loss": 0.25,
  "take_profit": 0.25,
  "max_position": 10,
  
  "ladder_threshold_1": 0.7,
  "ladder_mult_1": 2,
  "ladder_threshold_2": 0.9,
  "ladder_mult_2": 4,
  "ladder_threshold_3": 1.1,
  "ladder_mult_3": 8,
  
  "strategy_path": "examples/01_simple_rsi.py",
  "strategy_params": {
    "rsi_period": 14,
    "oversold": 30,
    "overbought": 70
  }
}
```

## 命令行覆盖

命令行参数会覆盖配置文件中的值：

```bash
# 配置文件设置 investment=200
# 命令行指定 --investment 1000
# 最终使用 1000
python scripts/run.py --config configs/params.json --investment 1000
```

## 相关文档

- [根目录 README](../README.md)
- [脚本使用说明](../scripts/)
- [策略示例 + 教程](../examples/)
