from pathlib import Path
from docx import Document
from ..core.models import XMindDocument, Sheet, TopicNode
from .base import BaseImporter


class DocxImporter(BaseImporter):
    """Word 文档导入器（Word -> XMind）"""
    
    def parse(self) -> XMindDocument:
        """解析 Word 文档"""
        doc = Document(self.file_path)
        
        # 解析 Word 内容
        root_node = self._parse_docx_content(doc)
        
        # 创建 Sheet
        sheet_title = self.file_path.stem
        sheet = self._create_sheet(sheet_title, root_node)
        self.document.add_sheet(sheet)
        
        return self.document
    
    def _parse_docx_content(self, doc: Document) -> TopicNode:
        """解析 Word 内容，构建树结构"""
        # 查找第一个标题作为根节点
        root_title = self.file_path.stem
        nodes = []
        
        for para in doc.paragraphs:
            if para.style.name.startswith('Heading'):
                # 提取标题级别
                level = int(para.style.name.replace('Heading ', ''))
                title = para.text.strip()
                nodes.append((title, level))
        
        # 如果没有找到标题，使用第一段作为根节点
        if not nodes:
            if doc.paragraphs:
                root_title = doc.paragraphs[0].text.strip()
        else:
            root_title = nodes[0][0]
            nodes = nodes[1:]  # 移除根节点
        
        # 创建根节点
        root = TopicNode(title=root_title, level=0)
        
        # 构建树结构
        if nodes:
            self._build_tree_from_nodes(root, nodes)
        
        return root
    
    def _build_tree_from_nodes(self, parent: TopicNode, nodes: list):
        """根据节点列表构建树结构"""
        if not nodes:
            return
        
        i = 0
        while i < len(nodes):
            title, level = nodes[i]
            
            # 创建新节点
            new_node = TopicNode(title=title, level=level)
            
            # 如果是一级节点，添加到根节点
            if level == 1:
                parent.add_child(new_node)
                # 递归构建子节点
                children = []
                j = i + 1
                while j < len(nodes) and nodes[j][1] > level:
                    children.append(nodes[j])
                    j += 1
                
                if children:
                    self._build_tree_from_nodes(new_node, children)
                
                i = j
            else:
                # 查找父节点
                parent_node = self._find_parent_by_level(parent, level)
                if parent_node:
                    parent_node.add_child(new_node)
                i += 1
    
    def _find_parent_by_level(self, node: TopicNode, target_level: int) -> TopicNode:
        """根据级别查找父节点"""
        if node.level == target_level - 1:
            return node
        
        for child in reversed(node.children):
            result = self._find_parent_by_level(child, target_level)
            if result:
                return result
        
        return None
