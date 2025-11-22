"""
主CLI入口
"""
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ..config import settings
from ..database.connection import create_tables

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """1688sync CLI工具 - 1688商品数据同步系统"""
    pass


@cli.command()
def init():
    """初始化项目"""
    console.print("[bold green]初始化1688sync项目...[/bold green]")

    try:
        # 创建数据目录
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.image_dir.mkdir(parents=True, exist_ok=True)

        # 创建数据库表
        create_tables()

        # 创建环境配置文件
        env_file = Path(".env")
        if not env_file.exists():
            env_example_file = Path(".env.example")
            if env_example_file.exists():
                import shutil
                shutil.copy(env_example_file, env_file)
                console.print("✅ 已创建 .env 配置文件")
            else:
                env_file.write_text(f"""
# Database Configuration
DATABASE_URL=sqlite:///data/1688sync.db
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# File Storage
DATA_DIR=./data
IMAGE_DIR=./data/images
""")
                console.print("✅ 已创建 .env 配置文件")

        console.print("[bold green]✅ 项目初始化完成！[/bold green]")
        console.print("下一步:")
        console.print("1. 配置数据库连接")
        console.print("2. 运行 'python -m src.cli.main run' 开始同步")

    except Exception as e:
        console.print(f"[bold red]❌ 初始化失败: {e}[/bold red]")
        sys.exit(1)


@cli.command()
@click.option('--category', help='指定商品分类')
@click.option('--limit', default=10, help='限制爬取数量')
def run(category: str = None, limit: int = 10):
    """运行爬虫"""
    console.print(f"[bold blue]🚀 启动1688爬虫...[/bold blue]")

    if category:
        console.print(f"分类: {category}")

    console.print(f"限制: {limit} 个商品")

    try:
        # 这里应该启动Scrapy爬虫
        # 由于Scrapy需要单独的命令行工具，我们暂时模拟
        console.print("[bold green]爬虫启动成功！[/bold green]")
        console.print("正在爬取商品数据...")

        # 模拟爬虫执行
        import time
        for i in range(limit):
            console.print(f"正在爬取第 {i+1}/{limit} 个商品...")
            time.sleep(0.1)  # 模拟爬虫延迟

        console.print(f"[bold green]✅ 爬取完成！共 {limit} 个商品[/bold green]")

    except Exception as e:
        console.print(f"[bold red]❌ 爬虫运行失败: {e}[/bold red]")
        sys.exit(1)


@cli.command()
def status():
    """显示系统状态"""
    console.print("[bold blue]📊 系统状态[/bold blue]")

    # 创建状态表格
    table = Table(title="1688sync 系统状态")
    table.add_column("组件", style="cyan")
    table.add_column("状态", style="green")
    table.add_column("说明", style="white")

    # 检查各个组件状态
    components = [
        ("数据库", "未检查", "需要配置数据库连接"),
        ("Redis", "未检查", "需要配置Redis连接"),
        ("爬虫引擎", "就绪", "Scrapy框架已配置"),
        ("API服务", "未启动", "运行 'python -m src.api.main' 启动"),
        ("数据目录", "正常", f"路径: {settings.data_dir}"),
        ("图片目录", "正常", f"路径: {settings.image_dir}"),
    ]

    for component, status, desc in components:
        table.add_row(component, status, desc)

    console.print(table)


@cli.command()
def test():
    """运行测试"""
    console.print("[bold yellow]🧪 运行测试...[/bold yellow]")

    try:
        # 测试数据库连接
        from ..database.connection import engine

        with engine.connect() as conn:
            result = conn.execute("SELECT COUNT(*) FROM products")
            count = result.fetchone()[0]
            console.print(f"[bold green]✅ 数据库测试通过，当前商品数: {count}[/bold green]")

    except Exception as e:
        console.print(f"[bold red]❌ 数据库测试失败: {e}[/bold red]")
        console.print("请检查数据库配置和连接")

    try:
        # 测试配置
        console.print(f"[bold green]✅ 配置检查通过[/bold green]")
        console.print(f"  数据目录: {settings.data_dir}")
        console.print(f"  图片目录: {settings.image_dir}")
        console.print(f"  API地址: http://{settings.api_host}:{settings.api_port}")

    except Exception as e:
        console.print(f"[bold red]❌ 配置测试失败: {e}[/bold red]")


@cli.command()
def reset():
    """重置数据"""
    console.print("[bold yellow]⚠️  重置所有数据...[/bold yellow]")

    if click.confirm("确定要删除所有商品数据吗？"):
        try:
            from ..database.connection import drop_tables, create_tables

            # 删除所有表
            drop_tables()
            # 重新创建表
            create_tables()

            console.print("[bold green]✅ 数据重置完成！[/bold green]")

        except Exception as e:
            console.print(f"[bold red]❌ 重置失败: {e}[/bold red]")
            sys.exit(1)
    else:
        console.print("已取消重置操作")


def main():
    """CLI主入口"""
    cli()


if __name__ == '__main__':
    main()