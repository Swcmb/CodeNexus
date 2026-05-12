"""
关系提取器演示

展示如何使用codenexus的关系提取功能。
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from codenexus.parser import get_default_parser, CrossFileAnalyzer
from codenexus.models.core import RelationType


def demo_single_file_relationships():
    """演示单文件关系提取"""
    print("=== 单文件关系提取演示 ===")
    
    # 创建包含多种关系的Python代码
    sample_code = '''
import os
from pathlib import Path

class Animal:
    """动物基类"""
    def __init__(self, name):
        self.name = name
    
    def speak(self):
        pass

class Dog(Animal):
    """狗类，继承自Animal"""
    def __init__(self, name, breed):
        super().__init__(name)
        self.breed = breed
    
    def speak(self):
        return f"{self.name} says Woof!"
    
    def fetch(self):
        return f"{self.name} is fetching"

class Cat(Animal):
    """猫类，继承自Animal"""
    def speak(self):
        return f"{self.name} says Meow!"

def create_animals():
    """创建动物实例"""
    dog = Dog("Buddy", "Golden Retriever")
    cat = Cat("Whiskers")
    
    print(dog.speak())
    print(cat.speak())
    print(dog.fetch())
    
    return [dog, cat]

def main():
    """主函数"""
    animals = create_animals()
    
    for animal in animals:
        sound = animal.speak()
        print(f"Animal sound: {sound}")

if __name__ == "__main__":
    main()
'''
    
    # 保存到临时文件
    temp_file = Path("temp_animals.py")
    temp_file.write_text(sample_code)
    
    try:
        # 获取解析器并解析文件
        parser = get_default_parser()
        result = parser.parse_file(str(temp_file))
        
        if result.success:
            print(f"✅ 成功解析文件: {result.parse_result.file_path}")
            print(f"🔍 找到 {len(result.parse_result.elements)} 个代码元素")
            print(f"🔗 找到 {len(result.parse_result.relationships)} 个关系")
            
            # 分析关系类型
            relationships = result.parse_result.relationships
            relationship_counts = {}
            
            for rel in relationships:
                rel_type = rel.type.value
                relationship_counts[rel_type] = relationship_counts.get(rel_type, 0) + 1
            
            print("\n📊 关系类型统计:")
            for rel_type, count in relationship_counts.items():
                print(f"  - {rel_type}: {count} 个")
            
            print("\n🔗 关系详情:")
            for i, rel in enumerate(relationships[:10]):  # 只显示前10个关系
                print(f"  {i+1}. {rel.type.value}: {rel.context}")
                if rel.metadata:
                    for key, value in rel.metadata.items():
                        if key in ['child_class', 'parent_class', 'caller', 'callee']:
                            print(f"     {key}: {value}")
        else:
            print(f"❌ 解析失败: {result.error_message}")
    
    finally:
        # 清理临时文件
        if temp_file.exists():
            temp_file.unlink()


def demo_cross_file_relationships():
    """演示跨文件关系分析"""
    print("\n=== 跨文件关系分析演示 ===")
    
    # 创建多个相关的Python文件
    files_content = {
        "base_classes.py": '''
class Vehicle:
    """交通工具基类"""
    def __init__(self, brand, model):
        self.brand = brand
        self.model = model
    
    def start(self):
        return f"{self.brand} {self.model} is starting"
    
    def stop(self):
        return f"{self.brand} {self.model} is stopping"

class Engine:
    """引擎类"""
    def __init__(self, horsepower):
        self.horsepower = horsepower
    
    def rev(self):
        return f"Engine revving at {self.horsepower} HP"
''',
        
        "cars.py": '''
from base_classes import Vehicle, Engine

class Car(Vehicle):
    """汽车类"""
    def __init__(self, brand, model, horsepower):
        super().__init__(brand, model)
        self.engine = Engine(horsepower)
    
    def accelerate(self):
        return f"{self.brand} {self.model} is accelerating"
    
    def rev_engine(self):
        return self.engine.rev()

class ElectricCar(Car):
    """电动汽车类"""
    def __init__(self, brand, model, battery_capacity):
        super().__init__(brand, model, 0)  # 电动车没有传统引擎
        self.battery_capacity = battery_capacity
    
    def charge(self):
        return f"Charging {self.brand} {self.model} battery"
''',
        
        "garage.py": '''
from cars import Car, ElectricCar
from base_classes import Vehicle

class Garage:
    """车库类"""
    def __init__(self):
        self.vehicles = []
    
    def add_vehicle(self, vehicle: Vehicle):
        self.vehicles.append(vehicle)
        return f"Added {vehicle.brand} {vehicle.model} to garage"
    
    def start_all(self):
        results = []
        for vehicle in self.vehicles:
            results.append(vehicle.start())
        return results

def create_sample_garage():
    """创建示例车库"""
    garage = Garage()
    
    # 添加不同类型的车辆
    car = Car("Toyota", "Camry", 200)
    electric_car = ElectricCar("Tesla", "Model 3", 75)
    
    garage.add_vehicle(car)
    garage.add_vehicle(electric_car)
    
    return garage
'''
    }
    
    # 创建临时文件
    temp_files = []
    for filename, content in files_content.items():
        temp_file = Path(filename)
        temp_file.write_text(content)
        temp_files.append(temp_file)
    
    try:
        # 解析所有文件
        parser = get_default_parser()
        parse_results = {}
        
        for temp_file in temp_files:
            result = parser.parse_file(str(temp_file))
            if result.success:
                parse_results[str(temp_file)] = result.parse_result
                print(f"✅ 解析文件: {temp_file}")
            else:
                print(f"❌ 解析失败: {temp_file} - {result.error_message}")
        
        if parse_results:
            # 使用跨文件分析器
            analyzer = CrossFileAnalyzer()
            cross_file_relationships = analyzer.analyze_project_relationships(parse_results)
            
            print(f"\n🌐 跨文件关系分析结果:")
            print(f"📁 分析了 {len(parse_results)} 个文件")
            print(f"🔗 找到 {len(cross_file_relationships)} 个跨文件关系")
            
            # 显示依赖图
            dependency_graph = analyzer.get_dependency_graph()
            print(f"\n📊 文件依赖图:")
            for file_path, dependencies in dependency_graph.items():
                if dependencies:
                    print(f"  {Path(file_path).name} 依赖于:")
                    for dep in dependencies:
                        print(f"    - {dep}")
            
            # 显示文件导出
            file_exports = analyzer.get_file_exports()
            print(f"\n📤 文件导出符号:")
            for file_path, exports in file_exports.items():
                if exports:
                    print(f"  {Path(file_path).name} 导出:")
                    for export in exports:
                        print(f"    - {export}")
            
            # 检查循环依赖
            cycles = analyzer.find_circular_dependencies()
            if cycles:
                print(f"\n⚠️ 发现 {len(cycles)} 个循环依赖:")
                for i, cycle in enumerate(cycles):
                    cycle_names = [Path(f).name for f in cycle]
                    print(f"  {i+1}. {' -> '.join(cycle_names)}")
            else:
                print(f"\n✅ 未发现循环依赖")
    
    finally:
        # 清理临时文件
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()


def demo_relationship_types():
    """演示不同类型的关系"""
    print("\n=== 关系类型演示 ===")
    
    relationship_examples = {
        "继承关系": '''
class Animal:
    pass

class Dog(Animal):
    pass
''',
        "组合关系": '''
class Engine:
    def __init__(self, power):
        self.power = power

class Car:
    def __init__(self):
        self.engine = Engine(200)
''',
        "调用关系": '''
def helper_function():
    return "help"

def main_function():
    result = helper_function()
    return result
''',
        "导入关系": '''
import os
from pathlib import Path
from typing import List, Dict

def use_imports():
    current_path = Path.cwd()
    return str(current_path)
'''
    }
    
    parser = get_default_parser()
    
    for relationship_type, code in relationship_examples.items():
        print(f"\n🔍 分析 {relationship_type}:")
        
        temp_file = Path(f"temp_{relationship_type.replace(' ', '_')}.py")
        temp_file.write_text(code)
        
        try:
            result = parser.parse_file(str(temp_file))
            
            if result.success:
                relationships = result.parse_result.relationships
                print(f"  找到 {len(relationships)} 个关系")
                
                for rel in relationships:
                    print(f"    - {rel.type.value}: {rel.context}")
            else:
                print(f"  解析失败: {result.error_message}")
        
        finally:
            if temp_file.exists():
                temp_file.unlink()


if __name__ == "__main__":
    print("🚀 codenexus 关系提取器演示")
    print("=" * 50)
    
    try:
        demo_single_file_relationships()
        demo_cross_file_relationships()
        demo_relationship_types()
        
        print("\n✨ 演示完成！")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()