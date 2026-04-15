"""
测试回测引擎
"""
import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from run import Engine, load_strategy
from helpers import create_test_csv, TEST_PARAMS, get_strategy_path


class TestEngine:
    """测试回测引擎"""
    
    def test_engine_init(self):
        """测试引擎初始化"""
        klines = create_test_csv(days=1, interval="1m")
        df = pd.read_csv(klines)
        StrategyCls = load_strategy(get_strategy_path())
        
        engine = Engine(StrategyCls, TEST_PARAMS.copy(), df)
        
        assert engine.klines is not None
        assert len(engine.klines) > 0
        assert engine.strategy is not None
        
        import os
        os.unlink(klines)
    
    def test_engine_run(self):
        """测试回测运行"""
        klines = create_test_csv(days=1, interval="1m")
        df = pd.read_csv(klines)
        StrategyCls = load_strategy(get_strategy_path())
        
        engine = Engine(StrategyCls, TEST_PARAMS.copy(), df)
        engine.run(verbose=False)
        
        assert len(engine.equity_curve) > 0
        assert len(engine.equity_curve) == len(df)
        
        first_record = engine.equity_curve[0]
        assert 'time' in first_record
        assert 'close' in first_record
        assert 'position_size' in first_record
        assert 'fund' in first_record
        
        import os
        os.unlink(klines)
    
    def test_engine_fund_tracking(self):
        """测试资金追踪"""
        klines = create_test_csv(days=1, interval="1m")
        df = pd.read_csv(klines)
        StrategyCls = load_strategy(get_strategy_path())
        
        params = TEST_PARAMS.copy()
        initial_fund = params['investment']
        
        engine = Engine(StrategyCls, params, df)
        engine.run(verbose=False)
        
        funds = [r['fund'] for r in engine.equity_curve]
        assert all(f >= 0 for f in funds)
        assert funds[0] == initial_fund
        
        import os
        os.unlink(klines)


class TestEngineEdgeCases:
    """测试边界情况"""
    
    def test_single_candle(self):
        """测试单根K线"""
        single_df = pd.DataFrame([{
            'time': '2025-01-01 00:00:00',
            'open': 3000,
            'high': 3010,
            'low': 2990,
            'close': 3005,
            'volume': 1000
        }])
        
        StrategyCls = load_strategy(get_strategy_path())
        engine = Engine(StrategyCls, TEST_PARAMS.copy(), single_df)
        engine.run(verbose=False)
        
        assert len(engine.equity_curve) == 1


class TestParallelEngine:
    """测试并行回测"""
    
    def test_parallel_run(self):
        """测试并行回测"""
        from run import run_parallel
        
        klines = create_test_csv(days=3, interval="1m")
        df = pd.read_csv(klines)
        df['time'] = pd.to_datetime(df['time'], utc=True)
        
        StrategyCls = load_strategy(get_strategy_path())
        strategy_path = get_strategy_path()
        result = run_parallel(df, StrategyCls, TEST_PARAMS.copy(), workers=2, strategy_path=strategy_path)
        
        assert 'equity_curve' in result
        assert len(result['equity_curve']) > 0
        assert result['months_processed'] >= 1
        
        import os
        os.unlink(klines)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
