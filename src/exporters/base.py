from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any
from ..core.models import XMindDocument, Sheet, TopicNode
from ..utils.file_manager import FileManager


class BaseExporter(ABC):
    """导出器基类"""
    
    def __init__(self, document: XMindDocument, file_manager: FileManager):
        self.document = document
        self.file_manager = file_manager
        
    @abstractmethod
    def export(self, output_path: Path, sheet_index: int = 0):
        """导出指定sheet到文件"""
        pass
    
    @abstractmethod
    def export_all_sheets(self, output_dir: Path):
        """导出所有sheet"""
        pass
    
    def _get_sheet(self, sheet_index: int = 0) -> Sheet:
        """获取指定sheet"""
        sheet = self.document.get_sheet(sheet_index)
        if not sheet:
            raise ValueError(f"Sheet index {sheet_index} out of range")
        return sheet
    
    def _process_images(self, node: TopicNode, output_dir: Path) -> List[str]:
        """处理节点中的图片，返回图片路径列表
        
        Args:
            output_dir: 输出目录（如 output/文件名/md/）
                       图片会保存到 output/文件名/images/
        """
        image_paths = []
        
        # 图片统一保存到 output/文件名/images/ 目录
        images_dir = output_dir.parent / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)
        
        for img_path_str in node.images:
            img_path = Path(img_path_str)
            if img_path.exists():
                output_img_path = images_dir / img_path.name
                import shutil
                shutil.copy2(img_path, output_img_path)
                image_paths.append(str(output_img_path))
        
        # 递归处理子节点
        for child in node.children:
            child_images = self._process_images(child, output_dir)
            image_paths.extend(child_images)
        
        return image_paths
