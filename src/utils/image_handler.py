from pathlib import Path
from PIL import Image
import base64
from io import BytesIO


class ImageHandler:
    """图片处理器：处理 XMind 中的图片"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def copy_image(self, src_path: Path, filename: str) -> Path:
        """复制图片到输出目录"""
        from shutil import copy2
        
        output_path = self.output_dir / filename
        copy2(src_path, output_path)
        return output_path
    
    def resize_image(self, image_path: Path, max_width: int = 800, max_height: int = 600) -> Path:
        """调整图片大小"""
        with Image.open(image_path) as img:
            # 计算新的尺寸
            width, height = img.size
            
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                
                # 调整大小
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 保存到临时文件
                output_path = self.output_dir / f"resized_{image_path.name}"
                resized_img.save(output_path)
                return output_path
            
            return image_path
    
    def image_to_base64(self, image_path: Path) -> str:
        """将图片转换为 base64 编码（用于嵌入 Markdown）"""
        with open(image_path, 'rb') as f:
            image_data = f.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            # 获取图片格式
            suffix = image_path.suffix.lower()
            mime_type = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.webp': 'image/webp'
            }.get(suffix, 'image/png')
            
            return f"data:{mime_type};base64,{base64_data}"
    
    def create_image_markdown(self, image_path: Path, title: str = '') -> str:
        """创建 Markdown 图片引用，并复制图片到输出目录"""
        if image_path.exists():
            self.copy_image(image_path, image_path.name)
        relative_path = Path('images') / image_path.name
        return f"![{title or 'image'}]({relative_path})"
    
    def create_image_html(self, image_path: Path, title: str = '') -> str:
        """创建 HTML 图片标签（用于 Word 导出）"""
        return f'<img src="{image_path}" alt="{title or "image"}" />'
