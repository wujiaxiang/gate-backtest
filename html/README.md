# HTML 报告使用指南

本目录包含回测结果的可视化 HTML 报告模板。

## 目录结构

```
html/
├── backtest_report.html   # 主报告模板
└── README.md              # 本文档
```

## 快速使用

### 1. 运行回测生成结果

```bash
python scripts/run.py \
    --market ETH_USDT \
    --interval 1d \
    --from 2025-01-01 \
    --to 2026-04-15
```

回测完成后，结果保存在 `results/时间戳/backtest_result.json`

### 2. 打开报告

```bash
# macOS
open html/backtest_report.html

# Windows
start html/backtest_report.html

# 或启动本地服务器（支持跨域）
cd html && python -m http.server 8080
# 访问 http://localhost:8080/backtest_report.html
```

### 3. 加载数据

1. 点击页面顶部的「选择回测结果 JSON 文件」按钮
2. 选择 `results/时间戳/backtest_result.json`
3. 即可查看可视化图表

**支持拖拽**：直接将 JSON 文件拖入页面即可加载

## 报告功能

### 关键指标仪表板

展示核心绩效指标：
- 总收益率 (%)
- 年化收益率 (%)
- 最大回撤 (%)
- 夏普比率
- 胜率 (%)
- 波动率 (%)

### 价格与累计收益率对照图

双 Y 轴图表：
- ETH 价格走势（折线图）
- 累计收益率（面积图）

### 日收益率与收益金额图

组合图表：
- 日收益率柱状图
- 累计收益金额折线图

### 日收益率分布直方图

展示日收益率的分布情况，帮助分析策略风险特征。

## 数据格式

`backtest_result.json` 结构：

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
      {"time": "2025-01-02T00:00:00", "price": 1210.5, "fund": 198.5, "position_size": -0.5}
    ],
    "trades": [
      {"entry_time": "...", "exit_time": "...", "pnl": 0.015}
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

## 自定义报告

`backtest_report.html` 是纯静态文件，用户可自行修改迭代。

### 修改样式

编辑 `<style>` 部分：

```css
/* 修改主题颜色 */
:root {
    --primary-color: #4CAF50;
    --bg-color: #1a1a2e;
}

/* 修改图表样式 */
.chart-container {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
}
```

### 添加新图表

```javascript
// 在 initCharts() 函数中添加新图表
function initCharts() {
    // 现有的图表初始化...
    
    // 添加自定义图表
    const ctx = document.getElementById('myChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: equityDates,
            datasets: [{
                label: '自定义指标',
                data: customData,
                borderColor: '#FFD700'
            }]
        }
    });
}
```

### 扩展指标展示

在 `updateMetrics()` 函数中添加新的指标展示：

```javascript
function updateMetrics(data) {
    // 现有指标...
    document.getElementById('total-return').textContent = /* ... */;
    
    // 添加新指标
    const metricsDiv = document.getElementById('custom-metrics');
    metricsDiv.innerHTML += `
        <div class="metric-card">
            <div class="metric-label">自定义指标</div>
            <div class="metric-value">${data.custom_metric}</div>
        </div>
    `;
}
```

## 相关文档

- [根目录 README](../README.md)
- [策略示例 + 教程](../examples/)
- [配置参数](../configs/)
