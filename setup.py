from setuptools import find_packages, setup

setup(
    name="synthetic-b2b-saas-platform-analytics",
    version="1.0.0",
    description="End-to-end analytics for a synthetic European B2B SaaS platform.",
    author="Artur Tolasov",
    package_dir={"": "data_generator/src"},
    packages=find_packages("data_generator/src"),
    python_requires=">=3.11",
    install_requires=[
        "numpy>=2.0",
        "pandas>=2.2",
        "tabulate>=0.9.0",
        "PyYAML>=6.0",
        "python-dotenv>=1.0",
        "psycopg[binary]>=3.2",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0",
            "pytest-cov>=5.0",
            "ruff>=0.6",
        ]
    },
    entry_points={
        "console_scripts": [
            "saas-platform=b2b_saas_platform_analytics.cli:main",
        ]
    },
)
