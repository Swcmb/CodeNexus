"""
codenexus主入口点

支持通过 python -m codenexus 运行命令行工具。
"""

from .cli import cli

if __name__ == '__main__':
    cli()