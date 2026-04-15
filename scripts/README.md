# 脚本使用说明

本目录包含回测框架的入口脚本和工具脚本。

## 目录结构

```
scripts/
├── README.md              # 本文档
├── run.py                 # 主入口脚本（合并版，支持并行）
└── export_results.py       # CSV 转 JSON 导出工具
```

## run.py - 主入口脚本

单一入口文件，整合了所有回测功能，支持命令行参数和并行回测。

### 基本用法

```bash
# 使用默认配置
python scripts/run.py --config configs/params.json

# 自定义参数
python scripts/run.py \
    --market ETH_USDT \
    --interval 1d \
    --from 2025-01-01 \
    --to 2026-04-15 \
    --investment 1000 \
    --leverage 50
```

### 命令行参数

#### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--market` | 交易对 | `ETH_USDT`, `BTC_USDT` |
| `--interval` | K线周期 | `1m`, `5m`, `1h`, `4h`, `1d`, `7d` |

#### 数据源参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--datasource` | 数据源类型 | `gate_history` |
| `--from` | 起始日期 | `2025-01-01` |
| `--to` | 结束日期 | `2026-04-15` |
| `--data-file` | 本地数据文件路径 | `data/xxx.csv` |
| `--save-data` | 保存下载的数据到本地 | false |

**数据源类型**：

| 值 | 说明 |
|----|------|
| `gate` | Gate.io 实时（ccxt） |
| `gate_history` | Gate.io 历史批量数据（推荐） |
| `binance` | 币安（ccxt） |
| `okx` | OKX（ccxt） |
| `hyperliquid` | Hyperliquid（ccxt） |

#### 回测参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--investment` | 初始投资金额 (USDT) | 200 |
| `--leverage` | 杠杆倍数 | 50 |
| `--commission` | 手续费率 | 0.0005 |
| `--direction` | 交易方向 | `short` |

#### 策略参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--strategy` | 策略文件路径 | 内置马丁格尔策略 |
| `--strategy-params` | 策略参数 (JSON) | 见配置文件 |

#### 性能参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--workers` | 并行 worker 数量 | CPU 核心数 |
| `--no-parallel` | 禁用并行，串行执行 | false |

#### 输出参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--output` | 结果输出目录 | `results/时间戳/` |
| `--config` | 配置文件路径 | 无 |

### 使用示例

#### 完整示例

```bash
python scripts/run.py \
    --market ETH_USDT \
    --interval 1d \
    --from 2025-01-01 \
    --to 2026-04-15 \
    --investment 200 \
    --leverage 50 \
    --datasource gate_history \
    --strategy examples/01_simple_rsi.py
```

#### 使用自定义策略

```bash
python scripts/run.py \
    --strategy my_strategy.py \
    --strategy-params '{"rsi_period": 20, "oversold": 25}' \
    --market BTC_USDT
```

#### 使用本地数据

```bash
python scripts/run.py \
    --data-file data/ETH_USDT_1d.csv \
    --strategy my_strategy.py
```

#### 并行回测控制

```bash
# 禁用并行（串行模式）
python scripts/run.py --no-parallel --market ETH_USDT

# 指定 4 个 worker
python scripts/run.py --workers 4 --market ETH_USDT
```

#### 从配置文件加载

```bash
python scripts/run.py --config configs/params.json
```

## export_results.py - 结果导出工具

将回测结果导出为不同格式。

### 基本用法

```bash
# 导出为 JSON
python scripts/export_results.py results/20260415_120000/equity.csv

# 导出为指定格式
python scripts/export_results.py results/20260415_120000/equity.csv --format json

# 指定输出文件
python scripts/export_results.py results/20260415_120000/equity.csv -o output.json
```

### 支持格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| JSON | `.json` | 适合程序读取 |
| CSV | `.csv` | 适合 Excel 分析 |

## 日志管理

运行脚本时，会自动管理日志：

- **当前日志**: `logs/backtest_latest.log`
- **历史日志**: `logs/backtest_YYYYMMDD_HHMMSS.log`（上次运行的备份）

### 查看日志

```bash
# 实时查看日志
tail -f logs/backtest_latest.log

# 查看最近错误
grep -i error logs/backtest_latest.log
```

## 常见问题

### Q: 如何查看所有可用参数？

```bash
python scripts/run.py --help
```

### Q: 数据量很大时如何加速？

框架默认启用并行回测（数据量 > 10000 条时自动开启）。如需手动控制：

```bash
# 增加 worker 数量
python scripts/run.py --workers 8 --market ETH_USDT
```

### Q: 如何调试策略？

```bash
# 启用详细日志
python scripts/run.py --market ETH_USDT -v

# 使用少量数据测试
python scripts/run.py \
    --market ETH_USDT \
    --from 2025-01-01 \
    --to 2025-02-01
```

## 相关文档

- [根目录 README](../README.md)
- [策略示例 + 教程](../examples/)
- [HTML 报告](../html/)
