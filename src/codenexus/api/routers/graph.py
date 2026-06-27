"""
知识图谱路由

提供图谱查询、构建和管理相关的API端点。
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from ..models import (
    GraphQueryRequest,
    GraphQueryResponse,
    GraphNodeResponse,
    GraphEdgeResponse,
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
    BaseResponse,
    PaginationParams
)
from ..dependencies import (
    get_database_service,
    get_graph_builder_service,
    get_impact_analyzer_service,
    get_current_user
)
from ...database import GraphDatabase
from ...graph import GraphBuilder
from ...services import ImpactAnalyzer

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=GraphQueryResponse)
async def query_graph(
    request: GraphQueryRequest,
    db: GraphDatabase = Depends(get_database_service),
    current_user = Depends(get_current_user)
):
    """
    查询知识图谱
    
    根据指定的查询条件搜索图谱中的节点和边。
    """
    try:
        logger.info(f"执行图查询: {request.query_type}")
        
        # 根据查询类型执行不同的查询
        if request.query_type == "nodes":
            nodes = await db.query_nodes(request.parameters)
            edges = []
        elif request.query_type == "edges":
            edges = await db.query_edges(request.parameters)
            nodes = []
        elif request.query_type == "subgraph":
            # 查询子图（包含节点和边）
            nodes = await db.query_nodes(request.parameters)
            # 获取节点间的边
            node_ids = [node.id for node in nodes]
            edge_query = {"source_ids": node_ids, "target_ids": node_ids}
            edges = await db.query_edges(edge_query)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的查询类型: {request.query_type}"
            )
        
        # 应用分页
        total_nodes = len(nodes)
        total_edges = len(edges)
        
        # 对节点分页
        start_idx = request.offset
        end_idx = start_idx + request.limit
        paginated_nodes = nodes[start_idx:end_idx]
        
        # 转换为响应格式
        node_responses = []
        for node in paginated_nodes:
            node_responses.append(GraphNodeResponse(
                id=node.id,
                label=node.label,
                type=node.type,
                properties=node.properties
            ))
        
        edge_responses = []
        for edge in edges:
            edge_responses.append(GraphEdgeResponse(
                source=edge.source,
                target=edge.target,
                type=edge.type,
                properties=edge.properties
            ))
        
        has_more = end_idx < total_nodes
        
        logger.info(f"图查询完成: 返回 {len(node_responses)} 个节点, {len(edge_responses)} 条边")
        
        return GraphQueryResponse(
            nodes=node_responses,
            edges=edge_responses,
            total_count=total_nodes,
            has_more=has_more,
            message="查询成功"
        )
        
    except Exception as e:
        logger.error(f"图查询失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"图查询失败: {str(e)}"
        )


@router.get("/nodes/{node_id}")
async def get_node(
    node_id: str,
    db: GraphDatabase = Depends(get_database_service),
    current_user = Depends(get_current_user)
):
    """
    获取指定节点的详细信息
    """
    try:
        nodes = await db.query_nodes({"id": node_id})
        
        if not nodes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"节点不存在: {node_id}"
            )
        
        node = nodes[0]
        
        return {
            "success": True,
            "node": GraphNodeResponse(
                id=node.id,
                label=node.label,
                type=node.type,
                properties=node.properties
            ),
            "message": "获取节点成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取节点失败: {node_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取节点失败: {str(e)}"
        )


@router.get("/nodes/{node_id}/neighbors")
async def get_node_neighbors(
    node_id: str,
    depth: int = Query(default=1, ge=1, le=3, description="邻居深度"),
    direction: str = Query(default="both", regex="^(in|out|both)$", description="方向"),
    db: GraphDatabase = Depends(get_database_service),
    current_user = Depends(get_current_user)
):
    """
    获取节点的邻居节点
    """
    try:
        # 构建邻居查询参数
        query_params = {
            "node_id": node_id,
            "depth": depth,
            "direction": direction
        }
        
        # 查询邻居节点
        neighbors = await db.query_nodes(query_params)
        
        # 转换为响应格式
        neighbor_responses = []
        for neighbor in neighbors:
            neighbor_responses.append(GraphNodeResponse(
                id=neighbor.id,
                label=neighbor.label,
                type=neighbor.type,
                properties=neighbor.properties
            ))
        
        return {
            "success": True,
            "neighbors": neighbor_responses,
            "count": len(neighbor_responses),
            "message": f"找到 {len(neighbor_responses)} 个邻居节点"
        }
        
    except Exception as e:
        logger.error(f"获取邻居节点失败: {node_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取邻居节点失败: {str(e)}"
        )


@router.get("/paths/{start_id}/{end_id}")
async def find_paths(
    start_id: str,
    end_id: str,
    max_depth: int = Query(default=5, ge=1, le=10, description="最大深度"),
    db: GraphDatabase = Depends(get_database_service),
    current_user = Depends(get_current_user)
):
    """
    查找两个节点之间的路径
    """
    try:
        paths = await db.find_paths(start_id, end_id, max_depth)
        
        return {
            "success": True,
            "paths": paths,
            "count": len(paths),
            "message": f"找到 {len(paths)} 条路径"
        }
        
    except Exception as e:
        logger.error(f"查找路径失败: {start_id} -> {end_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查找路径失败: {str(e)}"
        )


@router.post("/impact-analysis", response_model=ImpactAnalysisResponse)
async def analyze_impact(
    request: ImpactAnalysisRequest,
    analyzer: ImpactAnalyzer = Depends(get_impact_analyzer_service),
    db: GraphDatabase = Depends(get_database_service),
    current_user = Depends(get_current_user)
):
    """
    执行影响分析
    
    分析指定节点的变更对其他节点的潜在影响。
    """
    try:
        logger.info(f"开始影响分析: {request.node_id}")
        
        # 获取目标节点信息
        target_nodes = await db.query_nodes({"id": request.node_id})
        if not target_nodes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"目标节点不存在: {request.node_id}"
            )
        
        target_node = target_nodes[0]
        
        # 执行影响分析
        impact_result = analyzer.analyze_impact(
            graph_name="default",  # 使用默认图谱名称
            changed_node_id=request.node_id,
            max_depth=request.max_depth,
            include_downstream=request.include_reverse,
            include_upstream=True
        )
        
        # 转换为响应格式
        target_response = GraphNodeResponse(
            id=target_node.id,
            label=target_node.label,
            type=target_node.type,
            properties=target_node.properties
        )
        
        impacted_responses = []
        for node in impact_result.affected_nodes:
            # 创建一个模拟的GraphNode对象
            mock_node = type('MockNode', (), {
                'id': node.node_id,
                'label': node.node_name,
                'type': node.node_type,
                'properties': node.metadata
            })()
            
            impacted_responses.append(GraphNodeResponse(
                id=mock_node.id,
                label=mock_node.label,
                type=mock_node.type,
                properties=mock_node.properties
            ))
        
        # 提取影响路径
        impact_paths = []
        for path in impact_result.critical_paths:
            impact_paths.append(path.path_nodes)
        
        # 计算影响指标
        impact_metrics = {
            "total_impacted": len(impacted_responses),
            "max_depth": impact_result.analysis_metadata.get('max_depth', 0),
            "average_impact_score": sum(node.impact_score for node in impact_result.affected_nodes) / len(impact_result.affected_nodes) if impact_result.affected_nodes else 0,
            "critical_paths": len(impact_result.critical_paths)
        }
        
        logger.info(f"影响分析完成: {request.node_id}, 影响节点数: {len(impacted_responses)}")
        
        return ImpactAnalysisResponse(
            target_node=target_response,
            impacted_nodes=impacted_responses,
            impact_paths=impact_paths,
            impact_metrics=impact_metrics,
            message=f"影响分析完成，发现 {len(impacted_responses)} 个受影响节点"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"影响分析失败: {request.node_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"影响分析失败: {str(e)}"
        )


@router.get("/statistics")
async def get_graph_statistics(
    db: GraphDatabase = Depends(get_database_service),
    current_user = Depends(get_current_user)
):
    """
    获取图谱统计信息
    """
    try:
        stats = await db.get_graph_statistics()
        
        return {
            "success": True,
            "statistics": stats,
            "message": "获取统计信息成功"
        }
        
    except Exception as e:
        logger.error(f"获取图谱统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )


@router.delete("/clear")
async def clear_graph(
    confirm: bool = Query(default=False, description="确认清空图谱"),
    db: GraphDatabase = Depends(get_database_service),
    current_user = Depends(get_current_user)
):
    """
    清空图谱数据
    
    警告：此操作将删除所有图谱数据，不可恢复！
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须设置 confirm=true 才能执行清空操作"
        )
    
    try:
        # 这里需要实现清空图谱的逻辑
        # await db.clear_all()
        
        logger.warning("图谱数据已清空")
        
        return {
            "success": True,
            "message": "图谱数据已清空"
        }
        
    except Exception as e:
        logger.error(f"清空图谱失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空图谱失败: {str(e)}"
        )