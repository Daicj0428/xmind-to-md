import re
from pathlib import Path
from typing import List, Tuple, Optional
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
        
        # 跟踪代码块状态
        in_code_block = False
        code_block_fence = None
        
        # 收集标题和正文
        headings = []  # (level, title, body_lines)
        current_body = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 检测代码块开始/结束
            code_fence_match = re.match(r'^(```|~~~)(\w*)$', line.strip())
            if code_fence_match:
                if not in_code_block:
                    in_code_block = True
                    code_block_fence = code_fence_match.group(1)
                    # 保存代码块之前的正文
                    if current_body:
                        current_body.append(line)
                else:
                    # 结束代码块
                    in_code_block = False
                    code_block_fence = None
                    current_body.append(line)
                i += 1
                continue
            
            # 在代码块内：保存为正文，不解析标题
            if in_code_block:
                current_body.append(line)
                i += 1
                continue
            
            # 检测标题（不在代码块内）
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # 保存前一个标题的正文
                if headings:
                    headings[-1] = (headings[-1][0], headings[-1][1], current_body)
                
                headings.append((level, title, []))
                current_body = []
            else:
                # 非标题行，保存为正文
                if line.strip() or current_body:
                    current_body.append(line)
            
            i += 1
        
        # 保存最后一个标题的正文
        if headings and current_body:
            headings[-1] = (headings[-1][0], headings[-1][1], current_body)
        
        # 创建根节点（使用第一个标题或文件名）
        if headings:
            root_title = headings[0][1]
            root_body = headings[0][2]
            root = TopicNode(title=root_title, level=0)
            if root_body:
                root.notes = '\n'.join(root_body).strip()
            # 从第二个标题开始构建子树
            child_headings = headings[1:]
        else:
            root = TopicNode(title=self.file_path.stem, level=0)
            child_headings = []
        
        # 构建树结构
        if child_headings:
            self._build_tree_with_body(root, child_headings)
        
        return root
    
    def _build_tree_with_body(self, root: TopicNode, headings: List[Tuple[int, str, List[str]]]):
        """构建树结构，正文作为子节点添加"""
        # 节点栈，用于跟踪当前路径
        node_stack = [(root, 0)]  # (node, level)
        
        for level, title, body_lines in headings:
            # 创建标题节点
            new_node = TopicNode(title=title, level=level)
            
            # 添加正文作为子节点（如果有）
            if body_lines:
                body_text = '\n'.join(body_lines).strip()
                if body_text:
                    # 将正文内容直接作为子节点标题
                    body_node = TopicNode(title=body_text, level=level + 1)
                    new_node.add_child(body_node)
            
            # 找到正确的父节点
            while node_stack and node_stack[-1][1] >= level:
                node_stack.pop()
            
            if node_stack:
                parent_node = node_stack[-1][0]
                parent_node.add_child(new_node)
            else:
                root.add_child(new_node)
            
            # 将新节点压入栈
            node_stack.append((new_node, level))
