from setuptools import setup, find_packages

setup(
    name="gate-backtest",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "matplotlib>=3.7.0",
        "backtrader>=1.9.0",
        "ccxt>=4.0.0",
    ],
    python_requires=">=3.8",
)
