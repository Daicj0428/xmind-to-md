from pathlib import Path
from typing import List
from ..core.models import XMindDocument, Sheet, TopicNode
from .base import BaseImporter


class OutlineImporter(BaseImporter):
    """大纲文件导入器（Outline -> XMind）"""
    
    def parse(self) -> XMindDocument:
        """解析大纲文件"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析大纲内容
        root_node = self._parse_outline_content(content)
        
        # 创建 Sheet
        sheet_title = self.file_path.stem
        sheet = self._create_sheet(sheet_title, root_node)
        self.document.add_sheet(sheet)
        
        return self.document
    
    def _parse_outline_content(self, content: str) -> TopicNode:
        """解析大纲内容，构建树结构"""
        lines = content.split('\n')
        
        # 查找第一行作为根节点
        root_title = "Root"
        content_started = False
        content_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # 跳过空行和分隔线
            if not stripped or stripped == '=' * len(stripped) or stripped == '-' * len(stripped):
                content_started = True
                continue
            
            # 第一行作为根节点
            if not content_started:
                if root_title == "Root":
                    root_title = stripped
                    content_started = True
                else:
                    content_lines.append(line)
            else:
                content_lines.append(line)
        
        # 创建根节点
        root = TopicNode(title=root_title, level=0)
        
        # 解析子节点
        if content_lines:
            self._build_tree(root, content_lines)
        
        return root
    
    def _build_tree(self, parent: TopicNode, lines: List[str]):
        """递归构建树结构"""
        if not lines:
            return
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # 跳过空行
            if not stripped:
                i += 1
                continue
            
            # 计算缩进级别
            indent = len(line) - len(line.lstrip())
            level = indent // 2
            
            # 提取标题（去除项目符号）
            title = stripped
            title = title.lstrip('•◦○-').strip()
            
            # 创建新节点
            new_node = TopicNode(title=title, level=level)
            parent.add_child(new_node)
            
            # 查找子节点
            children_lines = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                next_indent = len(next_line) - len(next_line.lstrip())
                
                if next_indent > indent:
                    children_lines.append(next_line)
                    j += 1
                else:
                    break
            
            # 递归构建子节点
            if children_lines:
                self._build_tree(new_node, children_lines)
            
            i = j
