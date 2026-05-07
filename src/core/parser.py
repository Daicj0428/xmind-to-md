import json
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..utils.file_manager import FileManager
from .models import XMindDocument, Sheet, TopicNode


class XMindParser:
    """XMind 文件解析器（支持多sheet）"""
    
    def __init__(self, file_path: str, temp_dir: Optional[str] = None):
        self.file_path = Path(file_path)
        # 确保 temp_dir 是绝对路径
        if temp_dir:
            self.temp_dir = Path(temp_dir).resolve()
        else:
            self.temp_dir = Path('temp').resolve()
        self.file_manager = FileManager(self.temp_dir)
        self.document = XMindDocument(file_path=str(self.file_path))
        # 用于跟踪已使用的文件名，处理重名冲突
        self._used_filenames = set()
        
    def parse(self) -> XMindDocument:
        """解析 XMind 文件"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {self.file_path}")
        
        # 创建临时目录
        extract_dir = self.file_manager.create_extract_dir(self.file_path.stem)
        
        with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
            # 解压所有文件到临时目录
            zip_ref.extractall(extract_dir)
            
            # 读取 content.json
            content_path = extract_dir / 'content.json'
            if not content_path.exists():
                raise ValueError("无效的 XMind 文件：缺少 content.json")
            
            with open(content_path, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
            
            # 解析每个 sheet
            for sheet_data in content_data:
                sheet = self._parse_sheet(sheet_data, extract_dir)
                self.document.add_sheet(sheet)
        
        return self.document
    
    def _parse_sheet(self, sheet_data: Dict[str, Any], extract_dir: Path) -> Sheet:
        """解析单个工作表"""
        sheet_id = sheet_data.get('id', '')
        sheet_title = sheet_data.get('title', 'Untitled')
        theme = sheet_data.get('topic', {}).get('theme', {}).get('id', '')
        
        # 解析根主题
        root_topic_data = sheet_data.get('rootTopic', {})
        root_topic = self._parse_topic(root_topic_data, level=0, extract_dir=extract_dir)
        
        return Sheet(
            id=sheet_id,
            title=sheet_title,
            root_topic=root_topic,
            theme=theme
        )
    
    def _parse_topic(self, topic_data: Dict[str, Any], level: int, extract_dir: Path) -> TopicNode:
        """递归解析主题节点"""
        topic_id = topic_data.get('id', '')
        title = topic_data.get('title', '')
        
        # 提取图片
        images = self._extract_images(topic_data, extract_dir)
        
        # 提取备注
        notes = self._get_notes(topic_data)
        
        # 提取标签
        labels = topic_data.get('labels', [])
        
        # 提取标记
        markers = [m.get('markerId', '') for m in topic_data.get('markers', [])]
        
        # 创建节点
        node = TopicNode(
            title=title,
            level=level,
            notes=notes,
            labels=labels,
            markers=markers,
            images=images,
            id=topic_id
        )
        
        # 递归解析子节点 - 处理所有类型的子节点
        children_data = topic_data.get('children', {})
        # attached: 正常子主题, detached: 浮动主题, summary: 摘要
        all_children = []
        for child_type in ['attached', 'detached', 'summary']:
            all_children.extend(children_data.get(child_type, []))
        
        if not all_children and children_data:
            pass
        
        for child_data in all_children:
            child_node = self._parse_topic(child_data, level + 1, extract_dir)
            child_node.parent_id = topic_id
            node.add_child(child_node)
        
        return node
    
    def _extract_images(self, topic_data: Dict[str, Any], extract_dir: Path) -> List[str]:
        """提取主题中的图片（保留原始文件名，处理重名冲突）"""
        images = []
        
        # 检查 image 字段（可能是 dict 或 str）
        image_data = topic_data.get('image')
        if image_data:
            # 如果 image_data 是字符串，直接作为 src
            if isinstance(image_data, str):
                image_src = image_data
            else:
                image_src = image_data.get('src', '')
            
            if image_src:
                # 图片在 xmind 压缩包中的路径，移除可能的前缀
                clean_src = image_src.replace('xap:', '').replace('file://', '')
                image_path = extract_dir / clean_src
                if image_path.exists():
                    # 保留原始文件名
                    original_name = Path(clean_src).name
                    final_name = self._get_unique_filename(original_name)
                    
                    # 复制图片到临时目录的 images/ 中
                    import shutil
                    temp_img_path = extract_dir / 'images' / final_name
                    temp_img_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(image_path, temp_img_path)
                    
                    # 验证复制是否成功
                    if temp_img_path.exists():
                        images.append(str(temp_img_path))
                    else:
                        print(f"[WARNING] 图片复制失败: {image_path} -> {temp_img_path}")
                else:
                    # 源文件不存在，记录警告
                    print(f"[WARNING] 图片源文件不存在: {image_path} (src={image_src})")
        else:
            # 检查是否有子节点需要递归处理（调试用）
            pass
        
        return images
    
    def _get_unique_filename(self, filename: str) -> str:
        """获取唯一的文件名（处理重名冲突）"""
        if filename not in self._used_filenames:
            self._used_filenames.add(filename)
            return filename
        
        # 处理重名：在扩展名前添加序号
        name_part = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        while True:
            new_name = f"{name_part}_{counter}{suffix}"
            if new_name not in self._used_filenames:
                self._used_filenames.add(new_name)
                return new_name
            counter += 1
    
    def _get_notes(self, topic_data: Dict[str, Any]) -> str:
        """提取主题备注"""
        notes_data = topic_data.get('notes', {})
        if notes_data:
            return notes_data.get('plain', {}).get('content', '')
        return ''
    
    def get_flat_list(self, sheet_index: int = 0) -> List[Dict[str, Any]]:
        """获取指定sheet的扁平化节点列表"""
        sheet = self.document.get_sheet(sheet_index)
        if not sheet:
            return []
        
        result = []
        
        def traverse(node: TopicNode, parent_path: str = ''):
            current_path = f"{parent_path}/{node.title}" if parent_path else node.title
            result.append({
                'title': node.title,
                'level': node.level,
                'path': current_path,
                'notes': node.notes,
                'labels': node.labels,
                'markers': node.markers,
                'images': node.images
            })
            for child in node.children:
                traverse(child, current_path)
        
        traverse(sheet.root_topic)
        return result
