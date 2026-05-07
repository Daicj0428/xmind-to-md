from pathlib import Path
from typing import List
from ..core.models import XMindDocument, Sheet, TopicNode
from ..utils.file_manager import FileManager
from ..utils.image_handler import ImageHandler
from .base import BaseExporter


class OutlineExporter(BaseExporter):
    """大纲格式导出器（纯文本缩进格式）"""
    
    def export(self, output_path: Path, sheet_index: int = 0):
        """导出单个sheet为大纲格式"""
        sheet = self._get_sheet(sheet_index)
        
        # 创建图片处理器 - 图片保存在 output/文件名/images/ 目录
        images_dir = output_path.parent.parent / 'images'
        image_handler = ImageHandler(images_dir)
        
        # 生成大纲内容
        content = self._generate_outline(sheet.root_topic, image_handler)
        
        # 保存文件
        self.file_manager.save_file(content, output_path)
    
    def export_all_sheets(self, output_dir: Path):
        """导出所有sheet为大纲格式"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for i, sheet in enumerate(self.document.sheets):
            filename = f"{sheet.title or f'Sheet_{i+1}'}.txt"
            output_path = output_dir / filename
            self.export(output_path, sheet_index=i)
    
    def _generate_outline(self, node: TopicNode, image_handler: ImageHandler, indent_level: int = 0) -> str:
        """递归生成大纲内容"""
        if not node:
            return ''
        
        lines = []
        indent = '  ' * indent_level
        
        # 添加标题
        if node.title:
            if indent_level == 0:
                lines.append(f"{node.title}")
                lines.append("=" * len(node.title))
            else:
                if indent_level == 1:
                    lines.append(f"{indent}• {node.title}")
                else:
                    lines.append(f"{indent}◦ {node.title}")
            
            # 添加备注
            if node.notes:
                lines.append(f"{indent}  备注: {node.notes}")
            
            # 添加标签
            if node.labels:
                labels_str = ', '.join(node.labels)
                lines.append(f"{indent}  标签: [{labels_str}]")
            
            # 添加图片引用
            for img_path_str in node.images:
                img_path = Path(img_path_str)
                if img_path.exists():
                    lines.append(f"{indent}  [图片: {img_path.name}]")
        
        # 递归处理子节点
        for child in node.children:
            child_outline = self._generate_outline(child, image_handler, indent_level + 1)
            if child_outline:
                lines.append(child_outline)
        
        return '\n'.join(lines)
