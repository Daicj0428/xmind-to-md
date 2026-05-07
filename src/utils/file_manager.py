import shutil
import os
from pathlib import Path
from datetime import datetime
import uuid
from typing import Optional
from ..config import TempFilePolicy


class FileManager:
    """文件管理器：处理临时文件、输出文件、图片等"""
    
    def __init__(self, base_temp_dir: Path = None, policy: Optional[TempFilePolicy] = None):
        # 确保路径是绝对的
        if base_temp_dir:
            self.base_temp_dir = Path(base_temp_dir).resolve()
        else:
            self.base_temp_dir = Path('temp').resolve()
        
        self.base_output_dir = Path('output').resolve()
        
        # 保留策略
        self.policy = policy or TempFilePolicy()
        
        # 创建必要的目录
        self.base_temp_dir.mkdir(parents=True, exist_ok=True)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 打印调试信息
        print(f"[FileManager] base_temp_dir: {self.base_temp_dir}")
        print(f"[FileManager] base_output_dir: {self.base_output_dir}")
        
        # 如果配置了启动时清理，执行清理
        if self.policy.cleanup_on_startup:
            self.cleanup_temp()
    
    def create_extract_dir(self, file_stem: str) -> Path:
        """为解压文件创建临时目录"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        extract_dir = self.base_temp_dir / f"{file_stem}_{timestamp}"
        extract_dir.mkdir(parents=True, exist_ok=True)
        return extract_dir
    
    def create_output_dir(self, file_stem: str, format_type: str) -> Path:
        """创建输出目录"""
        output_dir = self.base_output_dir / file_stem / format_type
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def copy_image(self, src_path: Path, filename: str, output_dir: Path = None) -> Path:
        """复制图片到输出目录（output/文件名/images/）
        
        Args:
            src_path: 源图片路径
            filename: 保存的文件名
            output_dir: 目标目录（应为 output/文件名/images/）
        """
        if output_dir is None:
            # 如果没有指定 output_dir，打印警告并返回 None
            print(f"[WARNING] copy_image called without output_dir for {filename}")
            return None
        
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        
        shutil.copy2(src_path, output_path)
        return output_path
    
    def save_file(self, content: str, output_path: Path, encoding: str = 'utf-8'):
        """保存文本内容到文件"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding=encoding) as f:
            f.write(content)
    
    def save_binary_file(self, data: bytes, output_path: Path):
        """保存二进制文件"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(data)
    
    def create_download_package(self, source_dir: Path, output_filename: str) -> Path:
        """创建可下载的压缩包"""
        import zipfile
        
        # 确保输出文件名安全（只保留字母、数字、空格、横线、下划线、点号）
        safe_filename = "".join(c for c in output_filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        zip_path = self.base_temp_dir / f"{safe_filename}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            source_path = Path(source_dir)
            for root, dirs, files in os.walk(source_path):
                for file in files:
                    file_path = Path(root) / file
                    # 计算相对路径，用于 zip 中的文件结构
                    arcname = file_path.relative_to(source_path)
                    zipf.write(file_path, arcname)
        
        return zip_path
    
    def cleanup_temp(self, older_than_hours: int = None, force: bool = False):
        """根据策略清理临时文件
        
        Args:
            older_than_hours: 保留时间（小时），None 表示使用策略配置
            force: 如果为 True，强制清理所有临时文件（忽略保留时间）
        """
        import time
        
        if older_than_hours is None:
            older_than_hours = self.policy.retention_hours
        
        current_time = time.time()
        cutoff_time = current_time - (older_than_hours * 3600)
        
        cleaned = []
        
        # 强制清理模式：删除所有临时文件
        if force:
            for item in list(self.base_temp_dir.iterdir()):
                try:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                    cleaned.append(str(item))
                except Exception as e:
                    print(f"清理文件失败 {item}: {e}")
        else:
            # 按修改时间清理
            for item in list(self.base_temp_dir.iterdir()):
                try:
                    if item.stat().st_mtime < cutoff_time:
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            item.unlink(missing_ok=True)
                        cleaned.append(str(item))
                except Exception as e:
                    print(f"清理文件失败 {item}: {e}")
            
            # 如果配置了最大文件数量，清理最旧的文件
            if self.policy.max_file_count > 0:
                try:
                    all_files = list(self.base_temp_dir.iterdir())
                    if len(all_files) > self.policy.max_file_count:
                        # 按修改时间排序
                        all_files.sort(key=lambda x: x.stat().st_mtime)
                        # 删除最旧的文件，直到数量符合要求
                        for item in all_files[:-self.policy.max_file_count]:
                            try:
                                if item.is_dir():
                                    shutil.rmtree(item, ignore_errors=True)
                                else:
                                    item.unlink(missing_ok=True)
                                if str(item) not in cleaned:
                                    cleaned.append(str(item))
                            except Exception as e:
                                print(f"清理文件失败 {item}: {e}")
                except Exception as e:
                    print(f"清理文件数量限制失败: {e}")
            
            # 如果配置了最大文件大小，清理最大的文件
            if self.policy.max_file_size_mb > 0:
                try:
                    max_size = self.policy.max_file_size_mb * 1024 * 1024
                    for item in list(self.base_temp_dir.iterdir()):
                        try:
                            if item.is_file() and item.stat().st_size > max_size:
                                item.unlink(missing_ok=True)
                                if str(item) not in cleaned:
                                    cleaned.append(str(item))
                        except Exception as e:
                            print(f"清理大文件失败 {item}: {e}")
                except Exception as e:
                    print(f"清理大文件失败: {e}")
        
        return cleaned
    
    def get_temp_path(self, filename: str) -> Path:
        """获取临时文件路径"""
        return self.base_temp_dir / filename
    
    def get_output_path(self, filename: str, subdir: str = '') -> Path:
        """获取输出文件路径"""
        if subdir:
            output_dir = self.base_output_dir / subdir
        else:
            output_dir = self.base_output_dir
        
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / filename
