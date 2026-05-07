import os
from pathlib import Path
from typing import List
from ..core.models import XMindDocument, Sheet, TopicNode
from ..utils.file_manager import FileManager
from ..utils.image_handler import ImageHandler
from .base import BaseExporter


def escape_markdown_text(text: str) -> str:
    """转义 Markdown/HTML 特殊字符，避免被误解析为 HTML 标签或 Markdown 语法"""
    # 顺序：先转义 &，防止已有实体被二次转义
    text = text.replace('&', '&amp;')
    # 转义尖括号，防止被当作 HTML 标签（如 <RAID>、<组成设备>）
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text


class MarkdownExporter(BaseExporter):
    """Markdown 格式导出器"""
    
    def export(self, output_path: Path, sheet_index: int = 0):
        """导出单个sheet为Markdown"""
        sheet = self._get_sheet(sheet_index)
        
        # 创建图片处理器 - 图片保存在上级目录的 images/ 中
        # output_path: output/文件名/md/画布 1.md
        # images_dir: output/文件名/images/
        images_dir = output_path.parent.parent / 'images'
        image_handler = ImageHandler(images_dir)
        
        # 计算图片的相对路径（相对于 md 文件的位置）
        # 例如：md 文件在 output/文件名/md/，图片在 output/文件名/images/
        # 所以引用应该是 ../images/image_x.png
        rel_path = os.path.relpath(images_dir, output_path.parent)
        self._img_relative_prefix = Path(rel_path) / ''
        
        # 生成 Markdown 内容
        content = self._generate_markdown(sheet.root_topic, image_handler)
        
        # 保存文件
        self.file_manager.save_file(content, output_path)
    
    def export_all_sheets(self, output_dir: Path):
        """导出所有sheet为Markdown"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for i, sheet in enumerate(self.document.sheets):
            filename = f"{sheet.title or f'Sheet_{i+1}'}.md"
            output_path = output_dir / filename
            self.export(output_path, sheet_index=i)
    
    def _generate_markdown(self, node: TopicNode, image_handler: ImageHandler, level: int = 0, visited_nodes: set = None) -> str:
        """递归生成 Markdown 内容"""
        if visited_nodes is None:
            visited_nodes = set()
        
        if not node:
            return ''
        
        # 防止无限递归（如果有循环引用）
        if id(node) in visited_nodes:
            return ''
        visited_nodes.add(id(node))
        
        lines = []
        
        # 添加标题（仅当有标题时）
        if node.title:
            safe_title = escape_markdown_text(node.title)
            if level == 0:
                lines.append(f"# {safe_title}\n")
            else:
                indent = '#' * min(level + 1, 6)
                lines.append(f"{indent} {safe_title}")
        
        # 添加备注（无论是否有标题）
        if node.notes:
            safe_notes = escape_markdown_text(node.notes)
            lines.append(f"\n> **备注**: {safe_notes}\n")
        
        # 添加标签（无论是否有标题）
        if node.labels:
            labels_str = ' '.join([f'`{escape_markdown_text(label)}`' for label in node.labels])
            lines.append(f"\n{labels_str}\n")
        
        # 添加图片（无论是否有标题）
        for img_path_str in node.images:
            img_path = Path(img_path_str)
            # 如果没有标题，用默认alt文本（需要转义）
            alt_text = escape_markdown_text(node.title) if node.title else "image"
            # 生成正确的相对路径（md文件位置 -> 图片位置）
            # 强制使用正斜杠，兼容 Obsidian
            if hasattr(self, '_img_relative_prefix'):
                img_ref = (self._img_relative_prefix / img_path.name).as_posix()
            else:
                img_ref = f"images/{img_path.name}"
            
            # 复制图片到输出目录，只有成功后才添加引用
            img_copied = False
            if image_handler and img_path.exists():
                try:
                    copied = image_handler.copy_image(img_path, img_path.name)
                    if copied.exists():
                        img_copied = True
                    else:
                        print(f"[WARNING] 图片复制后不存在: {copied}")
                except Exception as e:
                    print(f"[WARNING] 图片复制失败 {img_path}: {e}")
            elif not img_path.exists():
                print(f"[WARNING] 图片源文件不存在: {img_path}")
            
            # 只有图片成功复制后才添加引用
            if img_copied:
                img_md = f"![{alt_text}]({img_ref})"
                lines.append(f"\n{img_md}\n")
            else:
                # 可选：添加注释说明图片缺失
                lines.append(f"\n<!-- 图片缺失: {img_ref} -->\n")
        
        # 递归处理子节点
        for child in node.children:
            child_md = self._generate_markdown(child, image_handler, level + 1, visited_nodes)
            if child_md:
                lines.append(child_md)
        
        return '\n'.join(lines)
