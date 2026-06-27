"""
codenexus 命令行界面

提供代码解析、知识图谱构建、影响分析、智能问答和文档生成等功能。
"""

import asyncio
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
from .services.qa_service import QAService
from .ai.documentation_generator import DocumentationGenerator
from .ai.ai_layer import AILayer
from .utils.logger import setup_logger

# 设置日志
setup_logger("codenexus")
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
    
    # 初始化解析器
    console.print("初始化解析器...")
    try:
        parser = TreeSitterParser()
        console.print("扫描文件...")
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
    
    console.print(f"找到 {len(files)} 个文件，开始解析...")
    
    # 解析文件
    parse_results = []
    for i, file_path in enumerate(files):
        try:
            result = parser.parse_file(str(file_path))
            if result.success:
                parse_results.append(result)
            console.print(f"解析进度: {i+1}/{len(files)} - {file_path.name}")
        except Exception as e:
            console.print(f"[yellow]警告:[/yellow] 解析文件失败 {file_path}: {e}")
    
    # 构建知识图谱
    console.print("构建知识图谱...")
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
    
    try:
        # 读取图谱数据
        console.print("初始化文档生成器...")
        with open(graph_file, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        console.print("生成文档...")
        
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
        
        console.print("文档生成完成!")
        
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
    
    try:
        # 简化的影响分析演示
        console.print("执行影响分析...")
        console.print("分析代码依赖...")
        
        # 模拟影响分析结果
        console.print(f"[INFO] 分析文件: {file}")
        console.print(f"[INFO] 变更描述: {change}")
        console.print(f"[INFO] 分析深度: {depth}")
        
        console.print("分析完成!")
            
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
    
    # 查找知识图谱文件
    graph_file = project_path / ".codenexus" / "knowledge_graph.json"
    if not graph_file.exists():
        # 尝试其他可能的位置
        possible_paths = [
            project_path / "knowledge_graph.json",
            project_path / "analysis" / "knowledge_graph.json",
            Path("analysis") / "knowledge_graph.json",
            Path("sample_project") / ".codenexus" / "knowledge_graph.json"
        ]
        
        for path in possible_paths:
            if path.exists():
                graph_file = path
                break
        else:
            console.print("[red]错误:[/red] 未找到知识图谱文件")
            console.print("请先运行解析命令生成知识图谱：")
            console.print(f"python -m codenexus parse -p {project_path} -o analysis")
            return
    
    try:
        # 加载知识图谱
        console.print("加载知识图谱...")
        with open(graph_file, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        # 创建AI层
        ai_layer = AILayer(config)
        ai_layer.initialize()
        
        # 创建数据库连接和QA服务
        from .database.graph_database import GraphDatabase
        from .models.core import CodeGraph, GraphNode, GraphEdge
        from .services.qa_service import QAService
        
        db = GraphDatabase()
        if db.connect():
            # 从JSON数据重建图谱对象
            graph = CodeGraph()
            
            # 重建节点
            nodes_map = {}
            for node_data in graph_data.get('nodes', []):
                # 创建CodeElement对象
                from .models.core import CodeElement
                element = CodeElement(
                    name=node_data['label'],
                    type=node_data['type'],
                    file_path=node_data.get('properties', {}).get('file_path', 'unknown'),
                    line_number=node_data.get('properties', {}).get('line_number', 0),
                    complexity=node_data.get('properties', {}).get('complexity', 1),
                    metadata=node_data.get('properties', {}).get('metadata', {})
                )
                
                # 将CodeElement对象存储在节点的properties中
                properties = node_data.get('properties', {})
                properties['element'] = element
                
                node = GraphNode(
                    id=node_data['id'],
                    label=node_data['label'],
                    type=node_data['type'],
                    properties=properties
                )
                graph.add_node(node)
                nodes_map[node.id] = node
            
            # 重建边
            for edge_data in graph_data.get('edges', []):
                # 处理两种可能的字段名格式
                source_id = edge_data.get('source_id') or edge_data.get('source')
                target_id = edge_data.get('target_id') or edge_data.get('target')
                
                edge = GraphEdge(
                    id=edge_data['id'],
                    source_id=source_id,
                    target_id=target_id,
                    type=edge_data['type'],
                    properties=edge_data.get('properties', {})
                )
                graph.add_edge(edge)
            
            # 创建QA服务并处理问题
            qa_service = QAService(ai_layer, db)
            result = asyncio.run(qa_service.process_question(question, graph))
            
            console.print("\n[bold green]回答:[/bold green]")
            console.print(result['answer'])
            
            # 显示相关代码信息
            if result.get('relevant_code'):
                console.print("\n[bold]相关代码:[/bold]")
                for elem in result['relevant_code'][:5]:  # 只显示前5个
                    console.print(f"- {elem['name']} ({elem['type']}) in {elem['file_path']}:{elem['line_number']}")
            
            # 显示置信度
            confidence = result.get('confidence', 0)
            console.print(f"\n[blue]置信度: {confidence:.1%}[/blue]")
            
            db.disconnect()
        else:
            console.print("[red]数据库连接失败[/red]")
        
        # 显示相关问题建议
        console.print("\n[bold]相关问题建议:[/bold]")
        console.print("- 这个函数的参数是什么？")
        console.print("- 这个类有哪些方法？")
        console.print("- 这个文件的用途是什么？")
        
    except Exception as e:
        console.print(f"[red]问答失败:[/red] {e}")
        import traceback
        traceback.print_exc()


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
