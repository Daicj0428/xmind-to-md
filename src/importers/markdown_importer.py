import re
from pathlib import Path
from typing import List, Tuple
from ..core.models import XMindDocument, Sheet, TopicNode
from .base import BaseImporter


class MarkdownImporter(BaseImporter):
    """Markdown 文件导入器（Markdown -> XMind）"""
    
    def parse(self) -> XMindDocument:
        """解析 Markdown 文件"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析 Markdown 内容
        root_node = self._parse_markdown_content(content)
        
        # 创建 Sheet
        sheet_title = self.file_path.stem
        sheet = self._create_sheet(sheet_title, root_node)
        self.document.add_sheet(sheet)
        
        return self.document
    
    def _parse_markdown_content(self, content: str) -> TopicNode:
        """解析 Markdown 内容，构建树结构"""
        lines = content.split('\n')
        
        # 查找第一个标题作为根节点
        root_title = "Root"
        content_lines = []
        
        for i, line in enumerate(lines):
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                level = len(match.group(1))
                title = match.group(2)
                
                if i == 0:
                    # 第一个标题作为根节点
                    root_title = title
                else:
                    # 其他标题作为子节点
                    indent = '  ' * (level - 1)
                    content_lines.append(f"{indent}{title}")
        
        # 如果没有找到标题，使用文件名作为根节点
        root = TopicNode(title=root_title, level=0)
        
        # 解析子节点
        if content_lines:
            child_root = self._build_tree_from_lines(content_lines)
            root.children = child_root.children
        
        return root
    
    def _build_tree_from_lines(self, lines: List[str]) -> TopicNode:
        """根据缩进级别构建树结构"""
        if not lines:
            return TopicNode(title="Temp", level=-1)
        
        # 使用第一行作为临时根节点
        root = TopicNode(title="Temp", level=-1)
        
        # 解析每一行
        current_level = 0
        current_node = root
        
        for line in lines:
            # 计算缩进级别
            indent = len(line) - len(line.lstrip())
            level = indent // 2
            
            # 提取标题（去除 Markdown 标记）
            title = line.strip()
            title = re.sub(r'^#+\s+', '', title)  # 去除标题标记
            title = re.sub(r'[*_`~]', '', title)  # 去除格式标记
            
            # 创建新节点
            new_node = TopicNode(title=title, level=level)
            
            # 找到父节点
            if level == 0:
                # 顶层节点，添加到根节点
                root.add_child(new_node)
            else:
                # 查找父节点
                parent = self._find_parent(root, level)
                if parent:
                    parent.add_child(new_node)
        
        return root
    
    def _find_parent(self, node: TopicNode, target_level: int) -> TopicNode:
        """查找目标级别的父节点"""
        if node.level == target_level - 1:
            return node
        
        for child in reversed(node.children):
            result = self._find_parent(child, target_level)
            if result:
                return result
        
        return None
