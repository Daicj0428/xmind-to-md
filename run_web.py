"""Web 应用启动脚本"""
import sys
import os
from pathlib import Path
import webbrowser
import threading
import time

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from web.app import app
from src.config import get_config


def open_browser(port):
    """延迟打开浏览器"""
    time.sleep(1.5)
    webbrowser.open(f'http://127.0.0.1:{port}/')


if __name__ == '__main__':
    config = get_config()
    
    # 支持环境变量端口（Docker/K8s 场景）
    port = int(os.environ.get('PORT', 5000))
    
    print("\n" + "="*60)
    print("  XMind 转换工具 - Web 版")
    print("="*60)
    print(f"\n项目根目录: {config.project_root}")
    print(f"上传目录: {config.upload_folder}")
    print(f"输出目录: {config.output_folder}")
    print(f"临时目录: {config.temp_folder}")
    print(f"配置文件: {config.config_file}")
    print(f"\n监听端口: {port}")
    print("\n正在启动 Web 服务器...")
    print(f"\n访问地址: http://127.0.0.1:{port}/")
    print("按 Ctrl+C 停止服务器\n")
    print("="*60 + "\n")
    
    # 在新线程中打开浏览器（仅本地运行时）
    if os.environ.get('DOCKER_CONTAINER') != 'true':
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    
    # 启动 Flask 应用
    app.run(debug=False, host='0.0.0.0', port=port)
