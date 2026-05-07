"""全局配置管理"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json


@dataclass
class TempFilePolicy:
    """临时文件保留策略"""
    # 自动清理开关
    auto_cleanup: bool = True
    # 保留时间（小时），超过此时间的文件将被清理
    retention_hours: int = 24
    # 最大文件大小（MB），超过此大小的文件将被优先清理
    max_file_size_mb: int = 100
    # 最大文件数量，超过此数量的旧文件将被清理
    max_file_count: int = 100
    # 启动时是否清理
    cleanup_on_startup: bool = False
    # 定时清理间隔（分钟）
    cleanup_interval_minutes: int = 60

    def to_dict(self):
        return {
            'auto_cleanup': self.auto_cleanup,
            'retention_hours': self.retention_hours,
            'max_file_size_mb': self.max_file_size_mb,
            'max_file_count': self.max_file_count,
            'cleanup_on_startup': self.cleanup_on_startup,
            'cleanup_interval_minutes': self.cleanup_interval_minutes
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class AppConfig:
    """应用配置"""
    # 项目根目录
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    # 上传文件目录
    upload_folder: Path = None
    # 输出文件目录
    output_folder: Path = None
    # 临时文件目录
    temp_folder: Path = None
    # 最大上传文件大小（MB）
    max_upload_size_mb: int = 100
    # 临时文件保留策略
    temp_policy: TempFilePolicy = field(default_factory=TempFilePolicy)
    # 配置文件路径
    config_file: Path = None

    def __post_init__(self):
        if self.upload_folder is None:
            self.upload_folder = self.project_root / 'temp' / 'uploads'
        if self.output_folder is None:
            self.output_folder = self.project_root / 'output'
        if self.temp_folder is None:
            self.temp_folder = self.project_root / 'temp'
        if self.config_file is None:
            self.config_file = self.project_root / 'config.json'

    def load(self):
        """从配置文件加载"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if 'temp_policy' in data:
                    self.temp_policy = TempFilePolicy.from_dict(data['temp_policy'])
                if 'max_upload_size_mb' in data:
                    self.max_upload_size_mb = data['max_upload_size_mb']
            except Exception as e:
                print(f"加载配置文件失败: {e}")

    def save(self):
        """保存到配置文件"""
        try:
            data = {
                'temp_policy': self.temp_policy.to_dict(),
                'max_upload_size_mb': self.max_upload_size_mb
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def ensure_dirs(self):
        """确保所有目录存在"""
        self.upload_folder.mkdir(parents=True, exist_ok=True)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.temp_folder.mkdir(parents=True, exist_ok=True)


# 全局配置实例
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = AppConfig()
        _config.load()
        _config.ensure_dirs()
    return _config


def set_config(config: AppConfig):
    """设置全局配置"""
    global _config
    _config = config
