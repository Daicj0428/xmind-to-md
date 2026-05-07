from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any
from ..core.models import XMindDocument, Sheet, TopicNode


class BaseImporter(ABC):
    """反向导入器基类（其他格式 -> XMind）"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.document = XMindDocument(file_path=str(self.file_path))
    
    @abstractmethod
    def parse(self) -> XMindDocument:
        """解析源文件，返回 XMindDocument 对象"""
        pass
    
    def _create_sheet(self, title: str, root_node: TopicNode) -> Sheet:
        """创建 Sheet 对象"""
        return Sheet(
            id=self._generate_id(),
            title=title,
            root_topic=root_node
        )
    
    def _generate_id(self) -> str:
        """生成唯一 ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _build_tree(self, lines: List[str]) -> TopicNode:
        """根据缩进级别构建树结构"""
        if not lines:
            return TopicNode(title="Root", level=0)
        
        root = TopicNode(title=lines[0].strip(), level=0)
        stack = [(root, 0)]  # (node, level)
        
        for line in lines[1:]:
            # 计算缩进级别
            indent = len(line) - len(line.lstrip())
            level = indent // 2  # 假设每级缩进 2 个空格
            title = line.strip()
            
            # 创建新节点
            new_node = TopicNode(title=title, level=level)
            
            # 找到父节点
            while stack and stack[-1][1] >= level:
                stack.pop()
            
            if stack:
                stack[-1][0].add_child(new_node)
            
            stack.append((new_node, level))
        
        return root
