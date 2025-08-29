#!/usr/bin/env python3
"""
Anki写卡助手安装脚本
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README文件
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    with open(readme_path, 'r', encoding='utf-8') as f:
        long_description = f.read()

# 读取requirements.txt
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    with open(requirements_path, 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="anki-card-writing-assistant",
    version="1.0.0",
    author="Anki Card Writing Assistant Team",
    author_email="contact@example.com",
    description="基于大语言模型的Anki记忆卡片生成工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/oldsuns/anki-card-writing-assistant",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Education",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "web": [
            "flask>=2.3.0",
            "flask-cors>=4.0.0",
            "flask-socketio>=5.3.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "anki-assistant=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.yaml", "*.yml", "*.txt", "*.md"],
    },
    keywords="anki, flashcards, memory, learning, ai, llm, education",
    project_urls={
        "Bug Reports": "https://github.com/oldsuns/anki-card-writing-assistant/issues",
        "Source": "https://github.com/oldsuns/anki-card-writing-assistant",
        "Documentation": "https://github.com/oldsuns/anki-card-writing-assistant",
    },
)
