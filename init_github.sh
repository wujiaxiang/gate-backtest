#!/bin/bash
# Gate-Backtest GitHub 上传脚本

echo "=== Gate-Backtest GitHub 初始化 ==="
echo ""

# 1. 配置 Git 用户信息
echo "[1/5] 配置 Git 用户信息..."
echo "请输入你的 GitHub 用户名和邮箱："
read -p "用户名: " github_user
read -p "邮箱: " github_email

git config user.name "$github_user"
git config user.email "$github_email"

# 2. 初始化 Git 仓库
echo ""
echo "[2/5] 初始化 Git 仓库..."
git init
git add .
git commit -m "Initial commit: Gate-Backtest framework (backtrader + ccxt)"

# 3. 创建 GitHub 仓库
echo ""
echo "[3/5] 创建 GitHub 仓库..."
gh repo create gate-backtest --public --source=. --push

echo ""
echo "[4/5] 完成!"
echo ""
echo "=== 项目已上传到 GitHub ==="
echo ""
echo "下一步："
echo "1. 访问 https://github.com/$github_user/gate-backtest 查看仓库"
echo "2. 克隆仓库到本地"
echo "3. 运行回测: python scripts/run_backtest.py --symbol ETH/USDT --interval 1d --from 2025-01-01 --to 2026-04-15"
echo ""
