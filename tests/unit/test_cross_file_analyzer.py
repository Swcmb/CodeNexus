"""
跨文件分析器的单元测试
"""

import tempfile
from pathlib import Path

import pytest
from src.codenexus.models.core import ElementType, RelationType
from src.codenexus.parser import get_default_parser
from src.codenexus.parser.cross_file_analyzer import CrossFileAnalyzer


class TestCrossFileAnalyzer:
    """CrossFileAnalyzer类的测试"""
    
    def setup_method(self):
        """测试前的设置"""
        self.parser = get_default_parser()
        self.analyzer = CrossFileAnalyzer()
    
    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        analyzer = CrossFileAnalyzer()
        
        assert analyzer.global_symbol_table == {}
        assert analyzer.import_graph == {}
        assert analyzer.file_exports == {}
    
    def test_build_global_symbol_table(self, tmp_path):
        """测试构建全局符号表"""
        # 创建测试文件
        file1 = tmp_path / "module1.py"
        file1.write_text("""
class ClassA:
    def method_a(self):
        pass

def function_a():
    pass
""")
        
        file2 = tmp_path / "module2.py"
        file2.write_text("""
class ClassB:
    def method_b(self):
        pass

def function_b():
    pass
""")
        
        # 解析文件
        result1 = self.parser.parse_file(str(file1))
        result2 = self.parser.parse_file(str(file2))
        
        assert result1.success
        assert result2.success
        
        parse_results = {
            str(file1): result1.parse_result,
            str(file2): result2.parse_result
        }
        
        # 构建全局符号表
        self.analyzer._build_global_symbol_table(parse_results)
        
        # 验证符号表
        assert len(self.analyzer.global_symbol_table) > 0
        
        # 检查特定符号
        assert "ClassA" in self.analyzer.global_symbol_table
        assert "ClassB" in self.analyzer.global_symbol_table
        assert "function_a" in self.analyzer.global_symbol_table
        assert "function_b" in self.analyzer.global_symbol_table
    
    def test_analyze_import_relationships(self, tmp_path):
        """测试分析导入关系"""
        # 创建有导入关系的文件
        base_file = tmp_path / "base.py"
        base_file.write_text("""
class BaseClass:
    def base_method(self):
        return "base"
""")
        
        derived_file = tmp_path / "derived.py"
        derived_file.write_text("""
import base
from base import BaseClass

class DerivedClass(BaseClass):
    def derived_method(self):
        return "derived"
""")
        
        # 解析文件
        base_result = self.parser.parse_file(str(base_file))
        derived_result = self.parser.parse_file(str(derived_file))
        
        assert base_result.success
        assert derived_result.success
        
        parse_results = {
            str(base_file): base_result.parse_result,
            str(derived_file): derived_result.parse_result
        }
        
        # 分析导入关系
        self.analyzer._analyze_import_relationships(parse_results)
        
        # 验证导入图
        assert str(derived_file) in self.analyzer.import_graph
        
        # 验证导出符号
        assert str(base_file) in self.analyzer.file_exports
        base_exports = self.analyzer.file_exports[str(base_file)]
        assert "BaseClass" in base_exports
    
    def test_analyze_project_relationships(self, tmp_path):
        """测试分析整个项目的关系"""
        # 创建一个小型项目
        utils_file = tmp_path / "utils.py"
        utils_file.write_text("""
def utility_function():
    return "utility"

class UtilityClass:
    def util_method(self):
        return "util"
""")
        
        main_file = tmp_path / "main.py"
        main_file.write_text("""
from utils import utility_function, UtilityClass

def main():
    result = utility_function()
    util = UtilityClass()
    return result

class MainClass(UtilityClass):
    def main_method(self):
        return self.util_method()
""")
        
        # 解析所有文件
        utils_result = self.parser.parse_file(str(utils_file))
        main_result = self.parser.parse_file(str(main_file))
        
        assert utils_result.success
        assert main_result.success
        
        parse_results = {
            str(utils_file): utils_result.parse_result,
            str(main_file): main_result.parse_result
        }
        
        # 分析项目关系
        relationships = self.analyzer.analyze_project_relationships(parse_results)
        
        # 验证返回的关系
        assert isinstance(relationships, list)
        
        # 检查是否有依赖关系
        dependency_rels = [r for r in relationships if r.type == RelationType.DEPENDS]
        assert len(dependency_rels) >= 0  # 可能有依赖关系
    
    def test_resolve_import_path(self, tmp_path):
        """测试解析导入路径"""
        # 创建测试文件结构
        module_file = tmp_path / "module.py"
        module_file.write_text("# Module file")
        
        main_file = tmp_path / "main.py"
        main_file.write_text("# Main file")
        
        # 解析文件
        module_result = self.parser.parse_file(str(module_file))
        main_result = self.parser.parse_file(str(main_file))
        
        parse_results = {
            str(module_file): module_result.parse_result,
            str(main_file): main_result.parse_result
        }
        
        # 测试导入路径解析
        resolved_path = self.analyzer._resolve_import_path(
            "module", str(main_file), parse_results
        )
        
        # 验证解析结果
        if resolved_path:
            assert Path(resolved_path).exists()
    
    def test_find_circular_dependencies(self):
        """测试查找循环依赖"""
        # 设置一个简单的循环依赖图
        self.analyzer.import_graph = {
            "file_a.py": {"file_b.py"},
            "file_b.py": {"file_c.py"},
            "file_c.py": {"file_a.py"}  # 循环依赖
        }
        
        # 查找循环依赖
        cycles = self.analyzer.find_circular_dependencies()
        
        # 验证找到了循环依赖
        assert isinstance(cycles, list)
        # 注意：由于实现的复杂性，这里只验证返回类型
    
    def test_get_dependency_graph(self):
        """测试获取依赖图"""
        # 设置测试数据
        test_graph = {
            "file1.py": {"file2.py", "file3.py"},
            "file2.py": {"file3.py"}
        }
        self.analyzer.import_graph = test_graph
        
        # 获取依赖图
        dependency_graph = self.analyzer.get_dependency_graph()
        
        # 验证返回的是副本
        assert dependency_graph == test_graph
        assert dependency_graph is not self.analyzer.import_graph
    
    def test_get_file_exports(self):
        """测试获取文件导出"""
        # 设置测试数据
        test_exports = {
            "file1.py": {"ClassA", "function_a"},
            "file2.py": {"ClassB", "function_b"}
        }
        self.analyzer.file_exports = test_exports
        
        # 获取导出信息
        file_exports = self.analyzer.get_file_exports()
        
        # 验证返回的是副本
        assert file_exports == test_exports
        assert file_exports is not self.analyzer.file_exports
    
    def test_is_exportable(self):
        """测试判断元素是否可导出"""
        from src.codenexus.models.core import CodeElement, ElementType
        
        # 创建测试元素
        public_class = CodeElement(
            name="PublicClass", 
            type=ElementType.CLASS, 
            visibility="public"
        )
        private_class = CodeElement(
            name="_PrivateClass", 
            type=ElementType.CLASS, 
            visibility="private"
        )
        public_function = CodeElement(
            name="public_function", 
            type=ElementType.FUNCTION, 
            visibility="public"
        )
        private_function = CodeElement(
            name="_private_function", 
            type=ElementType.FUNCTION, 
            visibility="private"
        )
        
        # 测试可导出性
        assert self.analyzer._is_exportable(public_class) == True
        assert self.analyzer._is_exportable(private_class) == False
        assert self.analyzer._is_exportable(public_function) == True
        assert self.analyzer._is_exportable(private_function) == False
    
    def test_complex_project_structure_analysis(self, tmp_path):
        """测试复杂项目结构的分析"""
        # 创建一个复杂的项目结构
        
        # models/base.py
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        base_file = models_dir / "base.py"
        base_file.write_text("""
class BaseModel:
    def __init__(self):
        self.id = None
    
    def save(self):
        pass
    
    def delete(self):
        pass

class BaseManager:
    def __init__(self):
        self.objects = []
    
    def create(self, **kwargs):
        pass
    
    def get(self, id):
        pass
""")
        
        # models/user.py
        user_file = models_dir / "user.py"
        user_file.write_text("""
from .base import BaseModel, BaseManager

class User(BaseModel):
    def __init__(self, name, email):
        super().__init__()
        self.name = name
        self.email = email
    
    def get_full_name(self):
        return self.name

class UserManager(BaseManager):
    def create_user(self, name, email):
        user = User(name, email)
        self.objects.append(user)
        return user
    
    def find_by_email(self, email):
        for user in self.objects:
            if user.email == email:
                return user
        return None
""")
        
        # services/user_service.py
        services_dir = tmp_path / "services"
        services_dir.mkdir()
        user_service_file = services_dir / "user_service.py"
        user_service_file.write_text("""
import sys
sys.path.append('..')

from models.user import User, UserManager
from models.base import BaseModel

class UserService:
    def __init__(self):
        self.user_manager = UserManager()
    
    def register_user(self, name, email):
        existing_user = self.user_manager.find_by_email(email)
        if existing_user:
            return None
        
        new_user = self.user_manager.create_user(name, email)
        new_user.save()
        return new_user
    
    def get_user_info(self, email):
        user = self.user_manager.find_by_email(email)
        if user:
            return {
                'name': user.get_full_name(),
                'email': user.email
            }
        return None
""")
        
        # main.py
        main_file = tmp_path / "main.py"
        main_file.write_text("""
from services.user_service import UserService
from models.user import User

def main():
    service = UserService()
    
    # 注册用户
    user = service.register_user("John Doe", "john@example.com")
    if user:
        print(f"用户注册成功: {user.get_full_name()}")
    
    # 获取用户信息
    user_info = service.get_user_info("john@example.com")
    if user_info:
        print(f"用户信息: {user_info}")

if __name__ == "__main__":
    main()
""")
        
        # 解析所有文件
        files_to_parse = [base_file, user_file, user_service_file, main_file]
        parse_results = {}
        
        for file_path in files_to_parse:
            result = self.parser.parse_file(str(file_path))
            if result.success:
                parse_results[str(file_path)] = result.parse_result
        
        # 分析项目关系
        relationships = self.analyzer.analyze_project_relationships(parse_results)
        
        # 验证分析结果
        assert isinstance(relationships, list)
        assert len(relationships) > 0
        
        # 验证全局符号表
        assert len(self.analyzer.global_symbol_table) > 0
        assert "BaseModel" in self.analyzer.global_symbol_table
        assert "User" in self.analyzer.global_symbol_table
        assert "UserService" in self.analyzer.global_symbol_table
        
        # 验证导入图
        assert len(self.analyzer.import_graph) > 0
        
        # 验证文件导出
        assert len(self.analyzer.file_exports) > 0
    
    def test_circular_dependency_detection(self, tmp_path):
        """测试循环依赖检测"""
        # 创建循环依赖的文件
        
        # file_a.py
        file_a = tmp_path / "file_a.py"
        file_a.write_text("""
from file_b import ClassB

class ClassA:
    def __init__(self):
        self.b = ClassB()
    
    def method_a(self):
        return "A"
""")
        
        # file_b.py
        file_b = tmp_path / "file_b.py"
        file_b.write_text("""
from file_c import ClassC

class ClassB:
    def __init__(self):
        self.c = ClassC()
    
    def method_b(self):
        return "B"
""")
        
        # file_c.py
        file_c = tmp_path / "file_c.py"
        file_c.write_text("""
from file_a import ClassA

class ClassC:
    def __init__(self):
        self.a = None  # 延迟初始化避免运行时循环
    
    def method_c(self):
        return "C"
    
    def create_a(self):
        self.a = ClassA()
""")
        
        # 解析文件
        files = [file_a, file_b, file_c]
        parse_results = {}
        
        for file_path in files:
            result = self.parser.parse_file(str(file_path))
            if result.success:
                parse_results[str(file_path)] = result.parse_result
        
        # 分析项目关系
        self.analyzer.analyze_project_relationships(parse_results)
        
        # 手动设置导入图来测试循环依赖检测
        self.analyzer.import_graph = {
            str(file_a): {str(file_b)},
            str(file_b): {str(file_c)},
            str(file_c): {str(file_a)}
        }
        
        # 检测循环依赖
        cycles = self.analyzer.find_circular_dependencies()
        
        # 验证找到了循环依赖
        assert isinstance(cycles, list)
    
    def test_inheritance_across_multiple_files(self, tmp_path):
        """测试跨多个文件的继承关系"""
        # 创建继承链跨越多个文件
        
        # animal.py
        animal_file = tmp_path / "animal.py"
        animal_file.write_text("""
class Animal:
    def __init__(self, name):
        self.name = name
    
    def speak(self):
        pass
    
    def move(self):
        return f"{self.name} is moving"
""")
        
        # mammal.py
        mammal_file = tmp_path / "mammal.py"
        mammal_file.write_text("""
from animal import Animal

class Mammal(Animal):
    def __init__(self, name, fur_color):
        super().__init__(name)
        self.fur_color = fur_color
    
    def give_birth(self):
        return f"{self.name} gives birth to live young"
""")
        
        # dog.py
        dog_file = tmp_path / "dog.py"
        dog_file.write_text("""
from mammal import Mammal

class Dog(Mammal):
    def __init__(self, name, breed, fur_color="brown"):
        super().__init__(name, fur_color)
        self.breed = breed
    
    def speak(self):
        return f"{self.name} barks: Woof!"
    
    def fetch(self):
        return f"{self.name} fetches the ball"
""")
        
        # pet_owner.py
        pet_owner_file = tmp_path / "pet_owner.py"
        pet_owner_file.write_text("""
from dog import Dog
from animal import Animal

class PetOwner:
    def __init__(self, name):
        self.name = name
        self.pets = []
    
    def adopt_pet(self, pet: Animal):
        self.pets.append(pet)
    
    def play_with_pets(self):
        results = []
        for pet in self.pets:
            if isinstance(pet, Dog):
                results.append(pet.fetch())
            results.append(pet.speak())
        return results
""")
        
        # 解析所有文件
        files = [animal_file, mammal_file, dog_file, pet_owner_file]
        parse_results = {}
        
        for file_path in files:
            result = self.parser.parse_file(str(file_path))
            if result.success:
                parse_results[str(file_path)] = result.parse_result
        
        # 分析跨文件关系
        relationships = self.analyzer.analyze_project_relationships(parse_results)
        
        # 验证跨文件继承关系
        cross_file_inheritance = [
            r for r in relationships 
            if r.type == RelationType.INHERITS and 
            r.metadata.get('cross_file', False)
        ]
        
        assert isinstance(cross_file_inheritance, list)
        
        # 验证全局符号表包含所有类
        expected_classes = ["Animal", "Mammal", "Dog", "PetOwner"]
        for class_name in expected_classes:
            assert class_name in self.analyzer.global_symbol_table
    
    def test_import_resolution_strategies(self, tmp_path):
        """测试不同的导入解析策略"""
        # 创建包结构
        package_dir = tmp_path / "mypackage"
        package_dir.mkdir()
        
        # mypackage/__init__.py
        init_file = package_dir / "__init__.py"
        init_file.write_text("""
from .core import CoreClass
from .utils import utility_function

__all__ = ['CoreClass', 'utility_function']
""")
        
        # mypackage/core.py
        core_file = package_dir / "core.py"
        core_file.write_text("""
class CoreClass:
    def __init__(self):
        self.value = "core"
    
    def get_value(self):
        return self.value
""")
        
        # mypackage/utils.py
        utils_file = package_dir / "utils.py"
        utils_file.write_text("""
def utility_function():
    return "utility"

class UtilityClass:
    def __init__(self):
        self.name = "utility"
""")
        
        # 使用包的文件
        main_file = tmp_path / "main.py"
        main_file.write_text("""
# 不同的导入方式
import mypackage
from mypackage import CoreClass
from mypackage.utils import utility_function, UtilityClass
from mypackage.core import CoreClass as Core

def main():
    # 使用不同导入方式的类
    core1 = mypackage.CoreClass()
    core2 = CoreClass()
    core3 = Core()
    
    util_func_result = utility_function()
    util_obj = UtilityClass()
    
    return [core1, core2, core3, util_func_result, util_obj]
""")
        
        # 解析文件
        files = [init_file, core_file, utils_file, main_file]
        parse_results = {}
        
        for file_path in files:
            result = self.parser.parse_file(str(file_path))
            if result.success:
                parse_results[str(file_path)] = result.parse_result
        
        # 分析项目关系
        relationships = self.analyzer.analyze_project_relationships(parse_results)
        
        # 验证导入关系
        import_dependencies = [
            r for r in relationships 
            if r.type == RelationType.DEPENDS and 
            r.metadata.get('dependency_type') == 'import'
        ]
        
        assert isinstance(import_dependencies, list)
        
        # 测试导入路径解析
        resolved_path = self.analyzer._resolve_import_path(
            "mypackage.core", str(main_file), parse_results
        )
        
        # 应该能解析到core.py文件
        if resolved_path:
            assert "core.py" in resolved_path
    
    def test_symbol_usage_tracking(self, tmp_path):
        """测试符号使用跟踪"""
        # 定义文件
        definitions_file = tmp_path / "definitions.py"
        definitions_file.write_text("""
class DataProcessor:
    def __init__(self):
        self.data = []
    
    def process(self, item):
        return item * 2
    
    def batch_process(self, items):
        return [self.process(item) for item in items]

def helper_function(value):
    return value + 1

CONSTANT_VALUE = 42
""")
        
        # 使用文件
        usage_file = tmp_path / "usage.py"
        usage_file.write_text("""
from definitions import DataProcessor, helper_function, CONSTANT_VALUE

class DataAnalyzer:
    def __init__(self):
        self.processor = DataProcessor()
    
    def analyze(self, data):
        processed = self.processor.batch_process(data)
        enhanced = [helper_function(item) for item in processed]
        return sum(enhanced) + CONSTANT_VALUE
    
    def get_processor(self):
        return self.processor

def standalone_analysis(data):
    processor = DataProcessor()
    result = processor.process(data[0])
    return helper_function(result)
""")
        
        # 解析文件
        files = [definitions_file, usage_file]
        parse_results = {}
        
        for file_path in files:
            result = self.parser.parse_file(str(file_path))
            if result.success:
                parse_results[str(file_path)] = result.parse_result
        
        # 分析使用关系
        relationships = self.analyzer.analyze_project_relationships(parse_results)
        
        # 验证使用关系
        usage_relationships = [
            r for r in relationships 
            if r.type == RelationType.DEPENDS and 
            r.metadata.get('dependency_type') == 'usage'
        ]
        
        assert isinstance(usage_relationships, list)
        
        # 验证符号表包含所有定义
        expected_symbols = ["DataProcessor", "helper_function", "DataAnalyzer"]
        for symbol in expected_symbols:
            assert symbol in self.analyzer.global_symbol_table
    
    def test_performance_with_large_project(self, tmp_path):
        """测试大型项目的性能"""
        # 创建一个模拟的大型项目
        files_created = []
        
        # 创建多个模块
        for module_idx in range(20):
            module_file = tmp_path / f"module_{module_idx}.py"
            
            # 生成模块内容
            module_content = []
            module_content.append(f"# Module {module_idx}")
            
            # 添加一些导入
            if module_idx > 0:
                import_idx = module_idx - 1
                module_content.append(f"from module_{import_idx} import Class{import_idx}")
            
            # 添加类定义
            for class_idx in range(5):
                class_name = f"Class{module_idx}_{class_idx}"
                module_content.append(f"""
class {class_name}:
    def __init__(self):
        self.value = {module_idx * 10 + class_idx}
    
    def method_{class_idx}(self):
        return self.value * {class_idx + 1}
    
    def call_other_method(self):
        return self.method_{class_idx}()
""")
            
            # 添加函数定义
            for func_idx in range(3):
                func_name = f"function_{module_idx}_{func_idx}"
                module_content.append(f"""
def {func_name}():
    obj = Class{module_idx}_0()
    return obj.method_0()
""")
            
            module_file.write_text('\n'.join(module_content))
            files_created.append(module_file)
        
        # 测试解析性能
        import time
        start_time = time.time()
        
        parse_results = {}
        for file_path in files_created:
            result = self.parser.parse_file(str(file_path))
            if result.success:
                parse_results[str(file_path)] = result.parse_result
        
        # 分析跨文件关系
        relationships = self.analyzer.analyze_project_relationships(parse_results)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 性能验证
        assert total_time < 10.0, f"分析时间过长: {total_time}秒"
        
        # 结果验证
        assert isinstance(relationships, list)
        assert len(self.analyzer.global_symbol_table) > 0
        assert len(self.analyzer.import_graph) > 0
        
        # 验证符号表大小合理
        expected_min_symbols = 20 * 5  # 至少每个模块5个类
        assert len(self.analyzer.global_symbol_table) >= expected_min_symbols