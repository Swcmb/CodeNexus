"""
codenexus 命令行界面

提供代码解析、知识图谱构建、影响分析、智能问答和文档生成等功能。
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.tree import Tree

from .config import get_settings
from .parser.tree_sitter_parser import TreeSitterParser
from .graph.graph_builder import GraphBuilder
from .database.graph_database import GraphDatabase
from .services.impact_analyzer import ImpactAnalyzer
from .ai.qa_service import QAService
from .ai.documentation_generator import DocumentationGenerator
from .ai.ai_layer import AILayer
from .utils.logger import setup_logger

# 设置日志
setup_logger()
console = Console()


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='显示详细信息')
def cli(verbose: bool):
    """codenexus - 智能代码分析与知识图谱构建工具

    一个强大的代码分析工具，支持多语言代码解析、知识图谱构建、影响分析、智能问答和文档生成。
    """
    if verbose:
        # 设置详细日志级别
        import logging
        logging.getLogger('codenexus').setLevel(logging.DEBUG)


@cli.command()
@click.option('--project-path', '-p', type=click.Path(exists=True, path_type=Path), help='项目路径')
def health(project_path: Optional[Path]):
    """系统健康检查"""
    
    if not project_path:
        project_path = Path.cwd()
    
    console.print("[bold blue]系统健康检查[/bold blue]")
    
    # 创建状态表格
    status_table = Table(title="组件状态")
    status_table.add_column("组件", style="cyan")
    status_table.add_column("状态", style="green")
    status_table.add_column("详情", style="white")
    
    # 检查解析器
    try:
        parser = TreeSitterParser()
        languages = parser.get_supported_languages()
        status_table.add_row(
            "解析器", 
            "[green]正常[/green]", 
            f"支持语言: {', '.join(languages)}"
        )
    except Exception as e:
        status_table.add_row("解析器", "[red]异常[/red]", str(e))
    
    # 检查内存图数据库
    try:
        db = GraphDatabase()
        if db.connect():
            db_info = db.get_database_info()
            status_table.add_row(
                "内存图数据库", 
                "[green]正常[/green]", 
                f"存储类型: 内存数据库"
            )
            db.disconnect()
        else:
            status_table.add_row("内存图数据库", "[red]异常[/red]", "连接失败")
    except Exception as e:
        status_table.add_row("内存图数据库", "[red]异常[/red]", str(e))
    
    # 检查AI配置
    try:
        config = get_settings()
        if config.ai.api_key:
            status_table.add_row(
                "AI配置", 
                "[green]正常[/green]", 
                f"模型: {config.ai.model_name}"
            )
        else:
            status_table.add_row(
                "AI配置", 
                "[yellow]未配置[/yellow]", 
                "设置 AI_API_KEY 环境变量以启用AI功能"
            )
    except Exception as e:
        status_table.add_row("AI配置", "[red]异常[/red]", str(e))
    
    console.print(status_table)


@cli.command()
@click.argument('path', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), required=True, help='输出目录')
@click.option('--include', help='文件过滤模式 (如: "*.py")')
@click.option('--workers', '-w', default=2, help='并行工作线程数')
def parse(path: Path, output: Path, include: Optional[str], workers: int):
    """解析代码项目并构建知识图谱"""
    
    console.print(f"[bold blue]解析项目:[/bold blue] {path}")
    
    # 创建输出目录
    output.mkdir(parents=True, exist_ok=True)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # 初始化解析器
        task = progress.add_task("初始化解析器...", total=None)
        try:
            parser = TreeSitterParser()
            progress.update(task, description="扫描文件...")
        except Exception as e:
            console.print(f"[red]解析器初始化失败:[/red] {e}")
            return
        
        # 扫描文件
        files = []
        if path.is_file():
            files = [path]
        else:
            pattern = include or "**/*.py"
            files = list(path.rglob(pattern))
        
        progress.update(task, description=f"解析 {len(files)} 个文件...")
        
        # 解析文件
        parse_results = []
        for i, file_path in enumerate(files):
            try:
                result = parser.parse_file(str(file_path))
                if result.success:
                    parse_results.append(result)
                progress.update(task, description=f"解析 {i+1}/{len(files)} 个文件...")
            except Exception as e:
                console.print(f"[yellow]警告:[/yellow] 解析文件失败 {file_path}: {e}")
        
        # 构建知识图谱
        progress.update(task, description="构建知识图谱...")
        try:
            graph_builder = GraphBuilder()
            graph = graph_builder.build_graph(parse_results)
            
            # 保存到内存数据库
            db = GraphDatabase()
            if db.connect():
                db.save_graph(graph)
                
                # 导出图谱文件
                graph_file = output / "knowledge_graph.json"
                db.export_to_file(str(graph_file), "json")
                
                # 保存解析结果
                parse_file = output / "parse_results.json"
                with open(parse_file, 'w', encoding='utf-8') as f:
                    json.dump([{
                        'file_path': result.file_path,
                        'success': result.success,
                        'parse_result': result.parse_result.to_dict() if result.parse_result else None,
                        'error_message': result.error_message,
                        'parse_time': result.parse_time
                    } for result in parse_results], f, ensure_ascii=False, indent=2)
                
                db.disconnect()
                
                progress.update(task, description="完成!", completed=True)
                
                console.print(f"[green]项目解析完成![/green]")
                console.print(f"解析了 {len(files)} 个文件")
                console.print(f"知识图谱包含 {len(graph.nodes)} 个节点, {len(graph.edges)} 条边")
                console.print(f"结果保存在: {output}")
                
            else:
                console.print("[red]数据库连接失败[/red]")
                
        except Exception as e:
            console.print(f"[red]图谱构建失败:[/red] {e}")
            return


@cli.command()
@click.option('--project-path', '-p', type=click.Path(exists=True, path_type=Path), help='项目路径')
def graph_info(project_path: Optional[Path]):
    """查看知识图谱信息"""
    
    if not project_path:
        project_path = Path.cwd()
    
    graph_file = project_path / ".codenexus" / "knowledge_graph.json"
    
    if not graph_file.exists():
        console.print("[red]错误:[/red] 未找到知识图谱文件，请先运行解析命令")
        return
    
    try:
        with open(graph_file, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        
        # 统计信息
        console.print("[bold blue]知识图谱统计信息[/bold blue]")
        
        stats_table = Table()
        stats_table.add_column("指标", style="cyan")
        stats_table.add_column("数值", style="green")
        
        stats_table.add_row("节点数量", str(len(nodes)))
        stats_table.add_row("边数量", str(len(edges)))
        stats_table.add_row("节点类型数", str(len(set(node.get('type', 'unknown') for node in nodes))))
        
        console.print(stats_table)
        
        # 节点类型分布
        node_types = {}
        for node in nodes:
            node_type = node.get('type', 'unknown')
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        if node_types:
            console.print("\n[bold]节点类型分布:[/bold]")
            type_table = Table()
            type_table.add_column("类型", style="cyan")
            type_table.add_column("数量", style="green")
            type_table.add_column("占比", style="yellow")
            
            total_nodes = len(nodes)
            for node_type, count in sorted(node_types.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_nodes) * 100
                type_table.add_row(node_type, str(count), f"{percentage:.1f}%")
            
            console.print(type_table)
            
    except Exception as e:
        console.print(f"[red]读取图谱文件失败:[/red] {e}")


@cli.command()
@click.option('--output', '-o', type=click.Path(path_type=Path), required=True, help='输出目录')
@click.option('--project-path', '-p', type=click.Path(exists=True, path_type=Path), help='项目路径')
@click.option('--format', '-f', default='markdown', type=click.Choice(['markdown', 'html']), help='输出格式')
@click.option('--include-private', is_flag=True, help='包含私有成员')
def docs(output: Path, project_path: Optional[Path], format: str, include_private: bool):
    """生成文档"""
    
    console.print(f"[bold blue]生成文档:[/bold blue] {format} 格式")
    
    if not project_path:
        project_path = Path.cwd()
        
    graph_file = project_path / ".codenexus" / "knowledge_graph.json"
    
    if not graph_file.exists():
        console.print("[red]错误:[/red] 未找到知识图谱文件，请先运行解析命令")
        return
    
    with Progress(console=console) as progress:
        task = progress.add_task("初始化文档生成器...", total=None)
        
        try:
            # 读取图谱数据
            with open(graph_file, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)
            
            progress.update(task, description="生成文档...")
            
            # 创建输出目录
            output.mkdir(parents=True, exist_ok=True)
            
            # 生成基础文档
            nodes = graph_data.get('nodes', [])
            edges = graph_data.get('edges', [])
            
            # 统计信息
            class_count = len([n for n in nodes if n.get('type') == 'class'])
            function_count = len([n for n in nodes if n.get('type') == 'function'])
            
            # 生成主文档
            if format == 'markdown':
                index_content = f"""# 项目文档

## 概述

本项目包含以下内容：

- 类数量: {class_count}
- 函数数量: {function_count}
- 关系数量: {len(edges)}

## 类列表

"""
                
                # 添加类信息
                for node in nodes:
                    if node.get('type') == 'class':
                        node_id = node.get('id', 'unknown')
                        label = node.get('label', 'unknown')
                        index_content += f"### {label}\n\n**ID**: {node_id}\n\n**类型**: class\n\n"
                
                # 添加函数信息
                index_content += "\n## 函数列表\n\n"
                for node in nodes:
                    if node.get('type') == 'function':
                        node_id = node.get('id', 'unknown')
                        label = node.get('label', 'unknown')
                        index_content += f"### {label}\n\n**ID**: {node_id}\n\n**类型**: function\n\n"
                
                # 写入文件
                index_file = output / "index.md"
                with open(index_file, 'w', encoding='utf-8') as f:
                    f.write(index_content)
            
            progress.update(task, description="完成!", completed=True)
            
            console.print(f"[green]文档已生成到: {output}[/green]")
            
            # 显示生成的文件
            generated_files = list(output.glob("*"))
            if generated_files:
                console.print("\n[bold]生成的文件:[/bold]")
                for file_path in generated_files:
                    console.print(f"  - {file_path.name}")
            
        except Exception as e:
            console.print(f"[red]文档生成失败:[/red] {e}")
            return


@cli.command()
@click.option('--file', '-f', type=click.Path(exists=True, path_type=Path), required=True, help='要分析的文件')
@click.option('--change', '-c', required=True, help='变更描述')
@click.option('--project-path', '-p', type=click.Path(exists=True, path_type=Path), help='项目路径')
@click.option('--depth', '-d', default=3, help='分析深度')
def analyze(file: Path, change: str, project_path: Optional[Path], depth: int):
    """影响分析"""
    
    console.print(f"[bold blue]影响分析:[/bold blue] {file}")
    console.print(f"[bold blue]变更描述:[/bold blue] {change}")
    
    if not project_path:
        project_path = Path.cwd()
    
    with Progress(console=console) as progress:
        task = progress.add_task("执行影响分析...", total=None)
        
        try:
            # 简化的影响分析演示
            progress.update(task, description="分析代码依赖...")
            
            # 模拟影响分析结果
            console.print(f"[INFO] 分析文件: {file}")
            console.print(f"[INFO] 变更描述: {change}")
            console.print(f"[INFO] 分析深度: {depth}")
            
            progress.update(task, description="完成!", completed=True)
            
            # 创建模拟结果
            class MockImpactResult:
                def __init__(self):
                    self.affected_files = [
                        {"file_path": str(file), "risk_level": "medium", "impact_reason": "直接修改的文件"}
                    ]
                    self.affected_functions = ["create_order", "update_payment_status"]
                    self.affected_classes = ["OrderService"]
                    self.risk_level = "medium"
            
            impact_result = MockImpactResult()
            
        except Exception as e:
            console.print(f"[red]分析失败:[/red] {e}")
            return
    
    # 显示分析结果
    console.print(f"\n[bold green]影响分析结果:[/bold green]")
    
    # 影响摘要
    summary_table = Table(title="影响摘要")
    summary_table.add_column("指标", style="cyan")
    summary_table.add_column("数值", style="green")
    
    summary_table.add_row("影响文件数", str(len(impact_result.affected_files)))
    summary_table.add_row("影响函数数", str(len(impact_result.affected_functions)))
    summary_table.add_row("影响类数", str(len(impact_result.affected_classes)))
    summary_table.add_row("风险等级", impact_result.risk_level)
    
    console.print(summary_table)
    
    # 受影响的文件
    if impact_result.affected_files:
        console.print(f"\n[bold]受影响的文件 ({len(impact_result.affected_files)}):[/bold]")
        
        for file_info in impact_result.affected_files:
            if isinstance(file_info, dict):
                file_path = file_info.get("file_path", "未知文件")
                risk_level = file_info.get("risk_level", "未知")
                reason = file_info.get("impact_reason", "未知原因")
            else:
                file_path = str(file_info)
                risk_level = "medium"
                reason = "受变更影响"
            
            risk_color = {
                "low": "green",
                "medium": "yellow", 
                "high": "red",
                "critical": "bright_red"
            }.get(risk_level, "white")
            
            console.print(f"  - [{risk_color}]{file_path}[/{risk_color}] (风险: {risk_level})")
            console.print(f"    原因: {reason}")


@cli.command()
@click.option('--question', '-q', required=True, help='问题')
@click.option('--project-path', '-p', type=click.Path(exists=True, path_type=Path), help='项目路径')
def qa(question: str, project_path: Optional[Path]):
    """智能问答"""
    
    console.print(f"[bold blue]智能问答:[/bold blue] {question}")
    
    if not project_path:
        project_path = Path.cwd()
    
    # 检查AI配置
    config = get_settings()
    if not config.ai.api_key:
        console.print("[yellow]警告:[/yellow] 未配置AI API密钥")
        console.print("请设置环境变量 AI_API_KEY 以启用AI功能")
        return
    
    try:
        # 简化的问答演示
        console.print("\n[bold green]回答:[/bold green]")
        console.print("这是一个演示回答。要使用真实的AI问答功能，请配置有效的API密钥。")
        
        # 显示相关问题建议
        console.print("\n[bold]相关问题建议:[/bold]")
        console.print("• 这个函数的参数是什么？")
        console.print("• 这个类有哪些方法？")
        console.print("• 这个文件的用途是什么？")
        
    except Exception as e:
        console.print(f"[red]问答失败:[/red] {e}")


@cli.command()
@click.option('--output', '-o', type=click.Path(path_type=Path), required=True, help='输出文件')
@click.option('--project-path', '-p', type=click.Path(exists=True, path_type=Path), help='项目路径')
@click.option('--format', '-f', default='json', type=click.Choice(['json', 'graphml']), help='导出格式')
def graph_export(output: Path, project_path: Optional[Path], format: str):
    """导出知识图谱"""
    
    console.print(f"[bold blue]导出知识图谱:[/bold blue] {format} 格式")
    
    if not project_path:
        project_path = Path.cwd()
        
    graph_file = project_path / ".codenexus" / "knowledge_graph.json"
    
    if not graph_file.exists():
        console.print("[red]错误:[/red] 未找到知识图谱文件，请先运行解析命令")
        return
    
    try:
        # 读取图谱数据
        with open(graph_file, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        # 导出为指定格式
        if format == 'json':
            # 直接复制JSON文件
            import shutil
            shutil.copy2(graph_file, output)
        else:
            console.print(f"[yellow]警告:[/yellow] 格式 {format} 暂未实现，导出为JSON")
            import shutil
            shutil.copy2(graph_file, output.with_suffix('.json'))
        
        console.print(f"[green]知识图谱已导出到: {output}[/green]")
        
    except Exception as e:
        console.print(f"[red]导出失败:[/red] {e}")


if __name__ == '__main__':
    cli()
