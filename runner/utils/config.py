"""
配置工具
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime


def load_params(filepath: str) -> Dict[str, Any]:
    """
    从JSON文件加载参数

    Args:
        filepath: JSON配置文件路径

    Returns:
        参数字典
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"配置文件不存在: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        params = json.load(f)

    # 处理日期参数
    if 'backtest_from' in params:
        try:
            dt = datetime.strptime(params['backtest_from'], '%Y-%m-%d')
            params['from_ts'] = int(dt.timestamp())
        except Exception:
            params['from_ts'] = 0

    if 'backtest_to' in params:
        try:
            dt = datetime.strptime(params['backtest_to'], '%Y-%m-%d')
            params['to_ts'] = int(dt.timestamp())
        except Exception:
            params['to_ts'] = int(datetime.now().timestamp())

    return params


def merge_params(base_params: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并参数

    Args:
        base_params: 基础参数
        overrides: 覆盖参数

    Returns:
        合并后的参数
    """
    result = base_params.copy()
    result.update(overrides)
    return result


def save_params(params: Dict[str, Any], filepath: str):
    """
    保存参数到JSON文件

    Args:
        params: 参数字典
        filepath: 保存路径
    """
    # 移除临时字段
    save_params = {k: v for k, v in params.items()
                   if k not in ['from_ts', 'to_ts']}

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(save_params, f, indent=2, ensure_ascii=False)


def validate_params(params: Dict[str, Any]) -> bool:
    """
    验证参数

    Args:
        params: 参数字典

    Returns:
        是否有效
    """
    required = ['market', 'interval', 'investment', 'leverage']

    for key in required:
        if key not in params:
            print(f"[错误] 缺少必需参数: {key}")
            return False

    # 验证数值范围
    if params.get('investment', 0) <= 0:
        print("[错误] 投资金额必须大于0")
        return False

    if params.get('leverage', 0) <= 0:
        print("[错误] 杠杆必须大于0")
        return False

    return True
