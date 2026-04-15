"""
测试结果导出
"""
import pytest
import pandas as pd
import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from run import export_results


class TestExportResults:
    """测试结果导出功能"""
    
    def setup_method(self):
        """每个测试前准备"""
        self.export_dir = tempfile.mkdtemp(prefix='test_export_')
    
    def teardown_method(self):
        """每个测试后清理"""
        if os.path.exists(self.export_dir):
            shutil.rmtree(self.export_dir)
    
    def test_export_creates_dated_dir(self):
        """测试导出创建目录"""
        equity = [
            {'time': '2025-01-01 00:00', 'close': 3000, 'position_size': 0, 'fund': 200},
            {'time': '2025-01-01 01:00', 'close': 3010, 'position_size': 0.5, 'fund': 210},
        ]
        klines = pd.DataFrame({
            'time': ['2025-01-01 00:00', '2025-01-01 01:00'],
            'close': [3000, 3010],
            'volume': [1000, 1100]
        })
        
        export_results(self.export_dir, klines, equity)
        
        assert os.path.exists(self.export_dir)
        assert len(os.listdir(self.export_dir)) > 0
    
    def test_export_equity_csv(self):
        """测试导出equity.csv"""
        equity = [
            {'time': '2025-01-01 00:00', 'close': 3000, 'position_size': 0, 'fund': 200},
            {'time': '2025-01-01 01:00', 'close': 3010, 'position_size': 0.5, 'fund': 210},
        ]
        klines = pd.DataFrame({
            'time': ['2025-01-01 00:00'],
            'close': [3000],
            'volume': [1000]
        })
        
        export_results(self.export_dir, klines, equity)
        
        equity_path = os.path.join(self.export_dir, 'equity.csv')
        assert os.path.exists(equity_path)
        
        df = pd.read_csv(equity_path)
        assert len(df) == 2
        assert 'fund' in df.columns
    
    def test_export_daily_equity(self):
        """测试导出daily_equity.csv（按天汇总）"""
        equity = [
            {'time': '2025-01-01 23:00', 'close': 3000, 'position_size': 0, 'fund': 200},
            {'time': '2025-01-02 01:00', 'close': 3010, 'position_size': 0.5, 'fund': 210},
            {'time': '2025-01-02 23:00', 'close': 3020, 'position_size': 0.3, 'fund': 215},
        ]
        klines = pd.DataFrame({
            'time': ['2025-01-01 23:00', '2025-01-02 01:00'],
            'close': [3000, 3010],
            'volume': [1000, 1100]
        })
        
        export_results(self.export_dir, klines, equity)
        
        daily_path = os.path.join(self.export_dir, 'daily_equity.csv')
        assert os.path.exists(daily_path)
        
        df = pd.read_csv(daily_path)
        assert len(df) == 2
        assert 'date' in df.columns
        assert 'cum_return' in df.columns
        assert 'daily_return' in df.columns
    
    def test_export_cum_return_calculation(self):
        """测试累计收益率计算（基于资金）"""
        equity = [
            {'time': '2025-01-01 00:00', 'close': 3000, 'position_size': 0, 'fund': 100},
            {'time': '2025-01-02 00:00', 'close': 3000, 'position_size': 0, 'fund': 110},
            {'time': '2025-01-03 00:00', 'close': 3000, 'position_size': 0, 'fund': 121},
        ]
        klines = pd.DataFrame({
            'time': ['2025-01-01 00:00', '2025-01-02 00:00'],
            'close': [3000, 3000],
            'volume': [1000, 1100]
        })
        
        export_results(self.export_dir, klines, equity)
        
        daily_path = os.path.join(self.export_dir, 'daily_equity.csv')
        df = pd.read_csv(daily_path)
        
        assert df['cum_return'].iloc[0] == 0
        assert abs(df['cum_return'].iloc[1] - 10) < 0.1
        assert abs(df['cum_return'].iloc[2] - 21) < 0.1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
