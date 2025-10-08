"""Setup file for backtesting service"""

from setuptools import setup, find_packages

setup(
    name="backtesting",
    version="1.0.0",
    description="Backtesting & Historical Data Infrastructure",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "httpx>=0.25.2",
        "sqlalchemy>=2.0.23",
        "asyncpg>=0.29.0",
        "psycopg2-binary>=2.9.9",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "numpy>=1.25.2",
        "pandas>=2.1.4",
        "python-dateutil>=2.8.2",
        "pytz>=2023.3",
        "python-dotenv>=1.0.0",
        "structlog>=23.2.0",
        "loguru>=0.7.2",
        "tenacity>=8.2.3",
        "alembic>=1.13.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-httpx>=0.26.0",
            "pytest-mock>=3.12.0",
            "pytest-cov>=4.1.0",
            "coverage>=7.3.2",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "isort>=5.12.0",
            "mypy>=1.7.1",
        ]
    },
)
