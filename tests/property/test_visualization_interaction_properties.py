"""
**Feature: code-weaver, Property 3: 可视化交互响应性**
**验证需求: 需求 2.2, 2.3, 2.4**

对于任意用户交互操作（点击节点、筛选条件、缩放），系统应该正确响应并更新可视化显示，
显示的信息应该与用户操作相匹配。
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from typing import Dict, List, Any, Optional, Tuple
import json
import random


# 数据生成策略
@st.composite
def generate_graph_node(draw):
    """生成图谱节点"""
    node_types = ['class', 'function', 'variable', 'module', 'interface']
    return {
        'id': draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        'label': draw(st.text(min_size=1, max_size=50)),
        'type': draw(st.sampled_from(node_types)),
        'position': {
            'x': draw(st.floats(min_value=0, max_value=1000)),
            'y': draw(st.floats(min_value=0, max_value=1000))
        },
        'data': {
            'name': draw(st.text(min_size=1, max_size=30)),
            'file_path': draw(st.text(min_size=1, max_size=100))
        }
    }


@st.composite
def generate_graph_edge(draw, node_ids):
    """生成图谱边"""
    assume(len(node_ids) >= 2)
    edge_types = ['inherits', 'calls', 'imports', 'uses', 'contains']
    source = draw(st.sampled_from(node_ids))
    target = draw(st.sampled_from([nid for nid in node_ids if nid != source]))
    
    return {
        'id': f"{source}_{target}_{draw(st.integers(min_value=1, max_value=1000))}",
        'source': source,
        'target': target,
        'type': draw(st.sampled_from(edge_types)),
        'weight': draw(st.floats(min_value=0.1, max_value=1.0))
    }


@st.composite
def generate_visualization_data(draw):
    """生成可视化数据"""
    # 生成节点
    nodes = draw(st.lists(generate_graph_node(), min_size=2, max_size=20))
    
    # 确保节点ID唯一
    seen_ids = set()
    unique_nodes = []
    for node in nodes:
        if node['id'] not in seen_ids:
            seen_ids.add(node['id'])
            unique_nodes.append(node)
    
    assume(len(unique_nodes) >= 2)
    node_ids = [node['id'] for node in unique_nodes]
    
    # 生成边
    edges = draw(st.lists(generate_graph_edge(node_ids), min_size=1, max_size=min(10, len(unique_nodes) * 2)))
    
    return {
        'nodes': unique_nodes,
        'edges': edges
    }


@st.composite
def generate_user_interaction(draw, visualization_data):
    """生成用户交互操作"""
    interaction_types = ['node_click', 'filter_change', 'zoom_change', 'search', 'layout_change']
    interaction_type = draw(st.sampled_from(interaction_types))
    
    if interaction_type == 'node_click':
        node = draw(st.sampled_from(visualization_data['nodes']))
        return {
            'type': 'node_click',
            'target': node['id'],
            'data': node
        }
    elif interaction_type == 'filter_change':
        node_types = list(set(node['type'] for node in visualization_data['nodes']))
        return {
            'type': 'filter_change',
            'filter_type': draw(st.sampled_from(['all'] + node_types)),
            'previous_filter': draw(st.sampled_from(['all'] + node_types))
        }
    elif interaction_type == 'zoom_change':
        return {
            'type': 'zoom_change',
            'zoom_level': draw(st.floats(min_value=0.1, max_value=3.0)),
            'previous_zoom': draw(st.floats(min_value=0.1, max_value=3.0))
        }
    elif interaction_type == 'search':
        # 从现有节点标签中选择搜索词，或生成随机搜索词
        if visualization_data['nodes'] and draw(st.booleans()):
            node = draw(st.sampled_from(visualization_data['nodes']))
            search_term = node['label'][:draw(st.integers(min_value=1, max_value=len(node['label'])))]
        else:
            search_term = draw(st.text(min_size=0, max_size=20))
        
        return {
            'type': 'search',
            'search_term': search_term,
            'previous_term': draw(st.text(min_size=0, max_size=20))
        }
    elif interaction_type == 'layout_change':
        layouts = ['dagre', 'force', 'circular', 'grid', 'breadthfirst', 'concentric']
        return {
            'type': 'layout_change',
            'layout': draw(st.sampled_from(layouts)),
            'previous_layout': draw(st.sampled_from(layouts))
        }


class VisualizationInteractionSimulator:
    """可视化交互模拟器"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.current_filter = 'all'
        self.current_zoom = 1.0
        self.current_search = ''
        self.current_layout = 'dagre'
        self.selected_nodes = set()
        self.highlighted_nodes = set()
        
    def apply_interaction(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """应用用户交互并返回响应"""
        interaction_type = interaction['type']
        
        if interaction_type == 'node_click':
            return self._handle_node_click(interaction)
        elif interaction_type == 'filter_change':
            return self._handle_filter_change(interaction)
        elif interaction_type == 'zoom_change':
            return self._handle_zoom_change(interaction)
        elif interaction_type == 'search':
            return self._handle_search(interaction)
        elif interaction_type == 'layout_change':
            return self._handle_layout_change(interaction)
        
        return {'success': False, 'error': f'Unknown interaction type: {interaction_type}'}
    
    def _handle_node_click(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """处理节点点击"""
        node_id = interaction['target']
        node_data = interaction['data']
        
        # 验证节点存在
        if not any(node['id'] == node_id for node in self.data['nodes']):
            return {'success': False, 'error': 'Node not found'}
        
        # 更新选中状态
        if node_id in self.selected_nodes:
            self.selected_nodes.remove(node_id)
        else:
            self.selected_nodes.add(node_id)
        
        # 高亮相关节点
        related_nodes = self._find_related_nodes(node_id)
        self.highlighted_nodes = related_nodes
        
        return {
            'success': True,
            'selected_node': node_id,
            'node_data': node_data,
            'highlighted_nodes': list(related_nodes),
            'action': 'node_selected' if node_id in self.selected_nodes else 'node_deselected'
        }
    
    def _handle_filter_change(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """处理过滤器变更"""
        filter_type = interaction['filter_type']
        previous_filter = interaction['previous_filter']
        
        self.current_filter = filter_type
        
        # 计算过滤后的节点
        if filter_type == 'all':
            filtered_nodes = self.data['nodes']
        else:
            filtered_nodes = [node for node in self.data['nodes'] if node['type'] == filter_type]
        
        # 计算相关的边
        filtered_node_ids = {node['id'] for node in filtered_nodes}
        filtered_edges = [
            edge for edge in self.data['edges']
            if edge['source'] in filtered_node_ids and edge['target'] in filtered_node_ids
        ]
        
        return {
            'success': True,
            'filter_type': filter_type,
            'previous_filter': previous_filter,
            'filtered_nodes': filtered_nodes,
            'filtered_edges': filtered_edges,
            'node_count': len(filtered_nodes),
            'edge_count': len(filtered_edges)
        }
    
    def _handle_zoom_change(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """处理缩放变更"""
        zoom_level = interaction['zoom_level']
        previous_zoom = interaction['previous_zoom']
        
        self.current_zoom = zoom_level
        
        return {
            'success': True,
            'zoom_level': zoom_level,
            'previous_zoom': previous_zoom,
            'zoom_changed': abs(zoom_level - previous_zoom) > 0.01
        }
    
    def _handle_search(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """处理搜索"""
        search_term = interaction['search_term']
        previous_term = interaction['previous_term']
        
        self.current_search = search_term
        
        # 查找匹配的节点
        matching_nodes = []
        if search_term.strip():
            for node in self.data['nodes']:
                if (search_term.lower() in node['label'].lower() or 
                    search_term.lower() in node['type'].lower() or
                    search_term.lower() in node['data'].get('name', '').lower()):
                    matching_nodes.append(node)
        
        # 更新高亮
        self.highlighted_nodes = {node['id'] for node in matching_nodes}
        
        return {
            'success': True,
            'search_term': search_term,
            'previous_term': previous_term,
            'matching_nodes': matching_nodes,
            'match_count': len(matching_nodes),
            'highlighted_nodes': list(self.highlighted_nodes)
        }
    
    def _handle_layout_change(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """处理布局变更"""
        layout = interaction['layout']
        previous_layout = interaction['previous_layout']
        
        self.current_layout = layout
        
        return {
            'success': True,
            'layout': layout,
            'previous_layout': previous_layout,
            'layout_changed': layout != previous_layout
        }
    
    def _find_related_nodes(self, node_id: str) -> set:
        """查找与指定节点相关的节点"""
        related = {node_id}
        
        # 查找直接连接的节点
        for edge in self.data['edges']:
            if edge['source'] == node_id:
                related.add(edge['target'])
            elif edge['target'] == node_id:
                related.add(edge['source'])
        
        return related
    
    def get_current_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            'filter': self.current_filter,
            'zoom': self.current_zoom,
            'search': self.current_search,
            'layout': self.current_layout,
            'selected_nodes': list(self.selected_nodes),
            'highlighted_nodes': list(self.highlighted_nodes)
        }


# 属性测试
@given(generate_visualization_data())
@settings(max_examples=50, deadline=5000)
def test_node_click_response_consistency(visualization_data):
    """
    属性测试：节点点击响应一致性
    对于任意节点点击操作，系统应该正确响应并更新选中状态
    """
    simulator = VisualizationInteractionSimulator(visualization_data)
    
    # 随机选择一个节点进行点击
    node = random.choice(visualization_data['nodes'])
    interaction = {
        'type': 'node_click',
        'target': node['id'],
        'data': node
    }
    
    # 应用交互
    response = simulator.apply_interaction(interaction)
    
    # 验证响应
    assert response['success'] == True, "节点点击应该成功"
    assert response['selected_node'] == node['id'], "响应应该包含正确的选中节点ID"
    assert response['node_data'] == node, "响应应该包含正确的节点数据"
    assert 'highlighted_nodes' in response, "响应应该包含高亮节点列表"
    assert node['id'] in response['highlighted_nodes'], "点击的节点应该被高亮"
    
    # 验证状态更新
    state = simulator.get_current_state()
    assert node['id'] in state['selected_nodes'], "节点应该被标记为选中"


@given(generate_visualization_data())
@settings(max_examples=50, deadline=5000)
def test_filter_response_accuracy(visualization_data):
    """
    属性测试：过滤器响应准确性
    对于任意过滤条件，系统应该返回正确的过滤结果
    """
    simulator = VisualizationInteractionSimulator(visualization_data)
    
    # 获取所有节点类型
    node_types = list(set(node['type'] for node in visualization_data['nodes']))
    
    # 测试每种节点类型的过滤
    for node_type in node_types:
        interaction = {
            'type': 'filter_change',
            'filter_type': node_type,
            'previous_filter': 'all'
        }
        
        response = simulator.apply_interaction(interaction)
        
        # 验证响应
        assert response['success'] == True, f"过滤器变更应该成功: {node_type}"
        assert response['filter_type'] == node_type, "响应应该包含正确的过滤类型"
        
        # 验证过滤结果
        filtered_nodes = response['filtered_nodes']
        for node in filtered_nodes:
            assert node['type'] == node_type, f"过滤后的节点类型应该匹配: {node['type']} != {node_type}"
        
        # 验证边的过滤
        filtered_edges = response['filtered_edges']
        filtered_node_ids = {node['id'] for node in filtered_nodes}
        for edge in filtered_edges:
            assert edge['source'] in filtered_node_ids, "过滤后的边源节点应该在过滤节点中"
            assert edge['target'] in filtered_node_ids, "过滤后的边目标节点应该在过滤节点中"


@given(generate_visualization_data())
@settings(max_examples=50, deadline=5000)
def test_search_matching_accuracy(visualization_data):
    """
    属性测试：搜索匹配准确性
    对于任意搜索词，系统应该返回所有匹配的节点
    """
    simulator = VisualizationInteractionSimulator(visualization_data)
    
    # 从现有节点中选择搜索词
    if visualization_data['nodes']:
        node = random.choice(visualization_data['nodes'])
        # 使用节点标签的一部分作为搜索词
        search_term = node['label'][:max(1, len(node['label']) // 2)]
        
        interaction = {
            'type': 'search',
            'search_term': search_term,
            'previous_term': ''
        }
        
        response = simulator.apply_interaction(interaction)
        
        # 验证响应
        assert response['success'] == True, "搜索应该成功"
        assert response['search_term'] == search_term, "响应应该包含正确的搜索词"
        
        # 验证搜索结果
        matching_nodes = response['matching_nodes']
        
        # 验证所有匹配节点确实包含搜索词
        for match_node in matching_nodes:
            node_matches = (
                search_term.lower() in match_node['label'].lower() or
                search_term.lower() in match_node['type'].lower() or
                search_term.lower() in match_node['data'].get('name', '').lower()
            )
            assert node_matches, f"匹配节点应该包含搜索词: {match_node['label']} 不包含 {search_term}"
        
        # 验证没有遗漏匹配的节点
        for data_node in visualization_data['nodes']:
            should_match = (
                search_term.lower() in data_node['label'].lower() or
                search_term.lower() in data_node['type'].lower() or
                search_term.lower() in data_node['data'].get('name', '').lower()
            )
            if should_match:
                assert any(mn['id'] == data_node['id'] for mn in matching_nodes), \
                    f"应该匹配的节点被遗漏: {data_node['label']}"


@given(generate_visualization_data(), st.floats(min_value=0.1, max_value=3.0))
@settings(max_examples=30, deadline=5000)
def test_zoom_response_consistency(visualization_data, zoom_level):
    """
    属性测试：缩放响应一致性
    对于任意缩放级别，系统应该正确更新缩放状态
    """
    simulator = VisualizationInteractionSimulator(visualization_data)
    
    previous_zoom = simulator.current_zoom
    interaction = {
        'type': 'zoom_change',
        'zoom_level': zoom_level,
        'previous_zoom': previous_zoom
    }
    
    response = simulator.apply_interaction(interaction)
    
    # 验证响应
    assert response['success'] == True, "缩放操作应该成功"
    assert response['zoom_level'] == zoom_level, "响应应该包含正确的缩放级别"
    assert response['previous_zoom'] == previous_zoom, "响应应该包含正确的之前缩放级别"
    
    # 验证状态更新
    state = simulator.get_current_state()
    assert state['zoom'] == zoom_level, "缩放状态应该被正确更新"
    
    # 验证缩放变化检测
    expected_changed = abs(zoom_level - previous_zoom) > 0.01
    assert response['zoom_changed'] == expected_changed, "缩放变化检测应该准确"


@given(generate_visualization_data())
@settings(max_examples=30, deadline=5000)
def test_layout_change_response(visualization_data):
    """
    属性测试：布局变更响应
    对于任意布局变更，系统应该正确响应
    """
    simulator = VisualizationInteractionSimulator(visualization_data)
    
    layouts = ['dagre', 'force', 'circular', 'grid', 'breadthfirst', 'concentric']
    new_layout = random.choice(layouts)
    previous_layout = simulator.current_layout
    
    interaction = {
        'type': 'layout_change',
        'layout': new_layout,
        'previous_layout': previous_layout
    }
    
    response = simulator.apply_interaction(interaction)
    
    # 验证响应
    assert response['success'] == True, "布局变更应该成功"
    assert response['layout'] == new_layout, "响应应该包含正确的新布局"
    assert response['previous_layout'] == previous_layout, "响应应该包含正确的之前布局"
    
    # 验证状态更新
    state = simulator.get_current_state()
    assert state['layout'] == new_layout, "布局状态应该被正确更新"
    
    # 验证布局变化检测
    expected_changed = new_layout != previous_layout
    assert response['layout_changed'] == expected_changed, "布局变化检测应该准确"


@given(generate_visualization_data(), st.data())
@settings(max_examples=30, deadline=5000)
def test_interaction_sequence_consistency(visualization_data, data):
    """
    属性测试：交互序列一致性
    对于任意交互序列，系统状态应该保持一致
    """
    simulator = VisualizationInteractionSimulator(visualization_data)
    
    # 生成随机交互序列
    interactions = []
    for _ in range(data.draw(st.integers(min_value=2, max_value=5))):
        interaction = data.draw(generate_user_interaction(visualization_data))
        interactions.append(interaction)
    
    # 应用所有交互
    responses = []
    for interaction in interactions:
        response = simulator.apply_interaction(interaction)
        responses.append(response)
        assert response['success'] == True, f"交互应该成功: {interaction['type']}"
    
    # 验证最终状态的一致性
    final_state = simulator.get_current_state()
    
    # 验证状态字段存在
    required_fields = ['filter', 'zoom', 'search', 'layout', 'selected_nodes', 'highlighted_nodes']
    for field in required_fields:
        assert field in final_state, f"最终状态应该包含字段: {field}"
    
    # 验证状态值的合理性
    assert isinstance(final_state['selected_nodes'], list), "选中节点应该是列表"
    assert isinstance(final_state['highlighted_nodes'], list), "高亮节点应该是列表"
    assert final_state['zoom'] > 0, "缩放级别应该大于0"


if __name__ == "__main__":
    # 运行属性测试
    pytest.main([__file__, "-v", "--tb=short"])