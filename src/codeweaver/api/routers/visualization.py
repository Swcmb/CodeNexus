"""
可视化路由

提供图谱可视化相关的API端点。
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from ..models import (
    VisualizationRequest,
    VisualizationResponse,
    VisualNodeResponse,
    VisualEdgeResponse,
    BaseResponse
)
from ..dependencies import (
    get_impact_visualizer_service,
    get_database_service,
    get_current_user
)
from ...services import ImpactVisualizer

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/graph", response_model=VisualizationResponse)
async def generate_graph_visualization(
    request: VisualizationRequest,
    visualizer: ImpactVisualizer = Depends(get_impact_visualizer_service),
    db_service = Depends(get_database_service),
    current_user = Depends(get_current_user)
):
    """
    生成图谱可视化数据
    
    根据指定的参数生成适合前端渲染的图谱可视化数据。
    """
    try:
        logger.info(f"生成可视化数据: 类型={request.graph_type}, 布局={request.layout}")
        
        # 根据图类型获取数据
        if request.graph_type == "full":
            # 获取完整图谱
            nodes = await db_service.query_nodes(request.filters or {})
            edges = await db_service.query_edges(request.filters or {})
        elif request.graph_type == "subgraph":
            # 获取子图
            if not request.filters or "node_ids" not in request.filters:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="子图类型需要提供 node_ids 参数"
                )
            node_ids = request.filters["node_ids"]
            nodes = await db_service.query_nodes({"ids": node_ids})
            edges = await db_service.query_edges({"source_ids": node_ids, "target_ids": node_ids})
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的图类型: {request.graph_type}"
            )
        
        # 限制节点数量
        if len(nodes) > request.max_nodes:
            nodes = nodes[:request.max_nodes]
            # 重新过滤边，只保留在节点集合中的边
            node_ids = {node.id for node in nodes}
            edges = [edge for edge in edges if edge.source in node_ids and edge.target in node_ids]
        
        # 生成可视化数据
        visualization_data = await visualizer.generate_graph_data(
            nodes=nodes,
            edges=edges,
            layout=request.layout
        )
        
        # 转换为响应格式
        visual_nodes = []
        for node_data in visualization_data.nodes:
            visual_nodes.append(VisualNodeResponse(
                id=node_data.id,
                label=node_data.label,
                type=node_data.type,
                x=node_data.x,
                y=node_data.y,
                size=node_data.size,
                color=node_data.color,
                properties=node_data.properties
            ))
        
        visual_edges = []
        for edge_data in visualization_data.edges:
            visual_edges.append(VisualEdgeResponse(
                source=edge_data.source,
                target=edge_data.target,
                type=edge_data.type,
                weight=edge_data.weight,
                color=edge_data.color,
                properties=edge_data.properties
            ))
        
        # 布局信息
        layout_info = {
            "algorithm": request.layout,
            "iterations": visualization_data.layout_iterations,
            "bounds": visualization_data.bounds
        }
        
        # 统计信息
        statistics = {
            "total_nodes": len(visual_nodes),
            "total_edges": len(visual_edges),
            "node_types": {},
            "edge_types": {}
        }
        
        # 统计节点类型
        for node in visual_nodes:
            node_type = node.type
            statistics["node_types"][node_type] = statistics["node_types"].get(node_type, 0) + 1
        
        # 统计边类型
        for edge in visual_edges:
            edge_type = edge.type
            statistics["edge_types"][edge_type] = statistics["edge_types"].get(edge_type, 0) + 1
        
        logger.info(f"可视化数据生成完成: {len(visual_nodes)} 个节点, {len(visual_edges)} 条边")
        
        return VisualizationResponse(
            nodes=visual_nodes,
            edges=visual_edges,
            layout_info=layout_info,
            statistics=statistics,
            message="可视化数据生成成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成可视化数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成可视化数据失败: {str(e)}"
        )


@router.post("/impact")
async def generate_impact_visualization(
    node_id: str,
    max_depth: int = 3,
    visualizer: ImpactVisualizer = Depends(get_impact_visualizer_service),
    current_user = Depends(get_current_user)
):
    """
    生成影响分析可视化
    
    为指定节点的影响分析结果生成可视化数据。
    """
    try:
        # 这里应该先执行影响分析，然后生成可视化
        # 目前返回模拟数据
        
        impact_visualization = {
            "center_node": {
                "id": node_id,
                "label": "目标节点",
                "x": 0,
                "y": 0,
                "size": 2.0,
                "color": "#ff4444"
            },
            "impacted_nodes": [
                {
                    "id": "node1",
                    "label": "受影响节点1",
                    "x": 100,
                    "y": 0,
                    "size": 1.5,
                    "color": "#ffaa44",
                    "impact_level": "high"
                },
                {
                    "id": "node2", 
                    "label": "受影响节点2",
                    "x": -100,
                    "y": 0,
                    "size": 1.2,
                    "color": "#ffdd44",
                    "impact_level": "medium"
                }
            ],
            "impact_edges": [
                {
                    "source": node_id,
                    "target": "node1",
                    "type": "impacts",
                    "weight": 0.8,
                    "color": "#ff6666"
                },
                {
                    "source": node_id,
                    "target": "node2",
                    "type": "impacts",
                    "weight": 0.5,
                    "color": "#ffaa66"
                }
            ]
        }
        
        return {
            "success": True,
            "visualization": impact_visualization,
            "message": "影响分析可视化生成成功"
        }
        
    except Exception as e:
        logger.error(f"生成影响分析可视化失败: {node_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成影响分析可视化失败: {str(e)}"
        )


@router.get("/layouts")
async def get_available_layouts():
    """
    获取可用的布局算法列表
    """
    layouts = [
        {
            "id": "force",
            "name": "力导向布局",
            "description": "基于物理模拟的力导向算法",
            "suitable_for": ["general", "small_to_medium"]
        },
        {
            "id": "hierarchical",
            "name": "层次布局",
            "description": "按层次结构排列节点",
            "suitable_for": ["tree", "dag", "hierarchy"]
        },
        {
            "id": "circular",
            "name": "环形布局",
            "description": "将节点排列成圆形",
            "suitable_for": ["small", "presentation"]
        },
        {
            "id": "grid",
            "name": "网格布局",
            "description": "将节点排列成网格",
            "suitable_for": ["uniform", "comparison"]
        }
    ]
    
    return {
        "success": True,
        "layouts": layouts,
        "default": "force",
        "message": f"获取到 {len(layouts)} 种布局算法"
    }


@router.get("/themes")
async def get_visualization_themes():
    """
    获取可视化主题列表
    """
    themes = [
        {
            "id": "default",
            "name": "默认主题",
            "colors": {
                "class": "#4CAF50",
                "method": "#2196F3", 
                "variable": "#FF9800",
                "interface": "#9C27B0"
            }
        },
        {
            "id": "dark",
            "name": "深色主题",
            "colors": {
                "class": "#66BB6A",
                "method": "#42A5F5",
                "variable": "#FFA726",
                "interface": "#AB47BC"
            }
        },
        {
            "id": "colorblind",
            "name": "色盲友好主题",
            "colors": {
                "class": "#1f77b4",
                "method": "#ff7f0e",
                "variable": "#2ca02c",
                "interface": "#d62728"
            }
        }
    ]
    
    return {
        "success": True,
        "themes": themes,
        "default": "default",
        "message": f"获取到 {len(themes)} 个可视化主题"
    }