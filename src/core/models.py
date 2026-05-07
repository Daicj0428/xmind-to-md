from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class TopicNode:
    """思维导图主题节点"""
    title: str
    level: int = 0
    children: List['TopicNode'] = field(default_factory=list)
    notes: str = ''
    labels: List[str] = field(default_factory=list)
    markers: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)  # 图片路径列表
    id: str = ''
    parent_id: str = ''
    
    def add_child(self, child: 'TopicNode'):
        """添加子节点"""
        self.children.append(child)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'title': self.title,
            'level': self.level,
            'notes': self.notes,
            'labels': self.labels,
            'markers': self.markers,
            'images': self.images,
            'children': [c.to_dict() for c in self.children]
        }


@dataclass
class Sheet:
    """XMind 工作表"""
    id: str
    title: str
    root_topic: TopicNode
    theme: str = ''
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'theme': self.theme,
            'root_topic': self.root_topic.to_dict()
        }


@dataclass
class XMindDocument:
    """XMind 文档（可能包含多个sheet）"""
    file_path: str
    sheets: List[Sheet] = field(default_factory=list)
    
    def add_sheet(self, sheet: Sheet):
        """添加工作表"""
        self.sheets.append(sheet)
    
    def get_sheet(self, index: int = 0) -> Optional[Sheet]:
        """获取指定索引的工作表"""
        if 0 <= index < len(self.sheets):
            return self.sheets[index]
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'file_path': self.file_path,
            'sheets': [s.to_dict() for s in self.sheets]
        }
