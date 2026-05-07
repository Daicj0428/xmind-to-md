import json
import zipfile
from pathlib import Path
from typing import Dict, Any
from ..core.models import XMindDocument, Sheet, TopicNode
from ..utils.file_manager import FileManager


class XMindExporter:
    """XMind 格式导出器（其他格式 -> XMind）"""
    
    def __init__(self, document: XMindDocument, file_manager: FileManager):
        self.document = document
        self.file_manager = file_manager
    
    def export(self, output_path: Path, sheet_index: int = 0):
        """导出为 XMind 文件"""
        sheet = self.document.get_sheet(sheet_index)
        if not sheet:
            raise ValueError(f"Sheet index {sheet_index} out of range")
        
        # 确保输出路径有 .xmind 扩展名
        if not str(output_path).endswith('.xmind'):
            output_path = Path(str(output_path) + '.xmind')
        
        # 创建临时目录
        temp_dir = self.file_manager.base_temp_dir / 'xmind_export' / output_path.stem
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成 content.json
        content_data = self._generate_content([sheet])
        
        with open(temp_dir / 'content.json', 'w', encoding='utf-8') as f:
            json.dump(content_data, f, ensure_ascii=False, indent=2)
        
        # 创建 XMind 文件（本质是 zip）
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加 content.json
            zipf.write(temp_dir / 'content.json', 'content.json')
            
            # 添加 manifest.json
            manifest = self._generate_manifest()
            manifest_path = temp_dir / 'manifest.json'
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            zipf.write(manifest_path, 'manifest.json')
            
            # 添加 metadata.json
            metadata = self._generate_metadata()
            metadata_path = temp_dir / 'metadata.json'
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            zipf.write(metadata_path, 'metadata.json')
        
        return output_path
    
    def export_all_sheets(self, output_dir: Path):
        """导出所有 Sheet 为单独的 XMind 文件"""
        output_dir.mkdir(parents=True, exist_ok=True)
        results = []
        
        for i, sheet in enumerate(self.document.sheets):
            output_path = output_dir / f"{sheet.title or f'Sheet_{i+1}'}.xmind"
            self.export(output_path, sheet_index=i)
            results.append(str(output_path))
        
        return results
    
    def _generate_content(self, sheets: list) -> list:
        """生成 content.json 数据"""
        content = []
        
        for sheet in sheets:
            sheet_data = {
                'id': sheet.id or self._generate_id(),
                'title': sheet.title or 'Untitled',
                'rootTopic': self._topic_to_dict(sheet.root_topic),
                'topic': {
                    'theme': {
                        'id': sheet.theme or 'default'
                    }
                }
            }
            content.append(sheet_data)
        
        return content
    
    def _topic_to_dict(self, node: TopicNode) -> Dict[str, Any]:
        """将 TopicNode 转换为字典"""
        topic_dict = {
            'id': node.id or self._generate_id(),
            'title': node.title or 'Untitled'
        }
        
        # 添加备注
        if node.notes:
            topic_dict['notes'] = {
                'plain': {
                    'content': node.notes
                }
            }
        
        # 添加标签
        if node.labels:
            topic_dict['labels'] = node.labels
        
        # 添加标记
        if node.markers:
            topic_dict['markers'] = [{'markerId': m} for m in node.markers]
        
        # 添加子节点
        if node.children:
            children_list = []
            for child in node.children:
                children_list.append(self._topic_to_dict(child))
            
            topic_dict['children'] = {
                'attached': children_list
            }
        
        return topic_dict
    
    def _generate_manifest(self) -> dict:
        """生成 manifest.json"""
        return {
            'file-entries': {
                'content.json': {}
            }
        }
    
    def _generate_metadata(self) -> dict:
        """生成 metadata.json"""
        return {
            'creator': {
                'name': 'XMind Converter',
                'version': '1.0'
            }
        }
    
    def _generate_id(self) -> str:
        """生成唯一 ID"""
        import uuid
        return str(uuid.uuid4())
