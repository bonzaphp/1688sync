#!/usr/bin/env python3
# Setup script for 1688sync CLI

from setuptools import setup, find_packages
from pathlib import Path

# 读取 README 文件
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# 读取 requirements.txt
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text(encoding="utf-8").strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="1688sync",
    version="1.0.0",
    author="1688sync Team",
    author_email="team@1688sync.com",
    description="1688数据同步和爬虫命令行工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/1688sync",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Database",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "1688sync=cli:cli",
            "sync1688=cli:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.md", "*.txt"],
        "config": ["*.yaml", "*.yml", "*.json"],
        "src": ["**/*.py"],
    },
    zip_safe=False,
    keywords="1688 sync crawler data-cli click",
    project_urls={
        "Bug Reports": "https://github.com/your-org/1688sync/issues",
        "Source": "https://github.com/your-org/1688sync",
        "Documentation": "https://1688sync.readthedocs.io/",
    },
)