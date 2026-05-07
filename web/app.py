from flask import Flask, render_template, request, jsonify, send_file
from pathlib import Path
import os
import zipfile
import sys
import threading
import time
from datetime import datetime

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.parser import XMindParser
from src.exporters.markdown import MarkdownExporter
from src.exporters.docx import DocxExporter
from src.exporters.outline import OutlineExporter
from src.exporters.xmind_exporter import XMindExporter
from src.importers.markdown_importer import MarkdownImporter
from src.importers.docx_importer import DocxImporter
from src.importers.outline_importer import OutlineImporter
from src.utils.file_manager import FileManager
from src.config import get_config, AppConfig, TempFilePolicy
from src.utils.monitoring import setup_metrics

# 获取全局配置
config = get_config()

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# Flask 配置
app.config['MAX_CONTENT_LENGTH'] = config.max_upload_size_mb * 1024 * 1024

# 集成 Prometheus 监控
app = setup_metrics(app)

# 文件管理器 - 使用配置中的路径和策略
file_manager = FileManager(config.temp_folder, policy=config.temp_policy)

# 定时清理任务
cleanup_thread = None
stop_cleanup = threading.Event()


def scheduled_cleanup():
    """定时清理任务"""
    while not stop_cleanup.is_set():
        if config.temp_policy.auto_cleanup and config.temp_policy.cleanup_interval_minutes > 0:
            time.sleep(config.temp_policy.cleanup_interval_minutes * 60)
            try:
                cleaned = file_manager.cleanup_temp()
                print(f"[定时清理] 已清理 {len(cleaned)} 个文件")
            except Exception as e:
                print(f"[定时清理] 失败: {e}")
        else:
            time.sleep(60)  # 如果自动清理关闭，每分钟检查一次


def start_cleanup_scheduler():
    """启动定时清理任务"""
    global cleanup_thread
    if cleanup_thread is None or not cleanup_thread.is_alive():
        stop_cleanup.clear()
        cleanup_thread = threading.Thread(target=scheduled_cleanup, daemon=True)
        cleanup_thread.start()
        print("[定时清理] 已启动")


def stop_cleanup_scheduler():
    """停止定时清理任务"""
    global cleanup_thread
    stop_cleanup.set()
    if cleanup_thread and cleanup_thread.is_alive():
        cleanup_thread.join(timeout=5)
        print("[定时清理] 已停止")


# 启动定时清理
start_cleanup_scheduler()


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config_api():
    """获取当前配置"""
    try:
        return jsonify({
            'success': True,
            'config': {
                'max_upload_size_mb': config.max_upload_size_mb,
                'temp_policy': config.temp_policy.to_dict()
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['POST'])
def update_config_api():
    """更新配置"""
    try:
        data = request.json
        
        if 'temp_policy' in data:
            policy_data = data['temp_policy']
            config.temp_policy = TempFilePolicy.from_dict(policy_data)
        
        if 'max_upload_size_mb' in data:
            config.max_upload_size_mb = data['max_upload_size_mb']
            app.config['MAX_CONTENT_LENGTH'] = config.max_upload_size_mb * 1024 * 1024
        
        # 保存配置到文件
        config.save()
        
        # 更新文件管理器的策略
        file_manager.policy = config.temp_policy
        
        # 重启定时清理任务
        stop_cleanup_scheduler()
        start_cleanup_scheduler()
        
        return jsonify({
            'success': True,
            'message': '配置已更新',
            'config': {
                'max_upload_size_mb': config.max_upload_size_mb,
                'temp_policy': config.temp_policy.to_dict()
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件（支持正向和反向转换）"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 获取上传模式（正向或反向）
        mode = request.form.get('mode', 'forward')
        
        # 根据模式验证文件类型
        if mode == 'forward':
            if not file.filename.endswith('.xmind'):
                return jsonify({'error': '只支持 .xmind 文件'}), 400
        else:  # reverse mode
            if not (file.filename.endswith('.md') or 
                    file.filename.endswith('.docx') or 
                    file.filename.endswith('.txt')):
                return jsonify({'error': '只支持 .md、.docx、.txt 文件'}), 400
        
        # 确保上传目录存在
        config.upload_folder.mkdir(parents=True, exist_ok=True)
        
        # 保存上传的文件
        filename = file.filename
        filepath = config.upload_folder / filename
        file.save(str(filepath))
        
        # 验证文件是否成功保存
        if not filepath.exists():
            return jsonify({'error': f'文件保存失败: {filepath}'}), 500
        
        # 记录上传指标
        from src.utils.monitoring import track_upload, track_upload_failure
        try:
            file_size = filepath.stat().st_size
            track_upload(file_size)
        except:
            track_upload_failure()
        
        # 根据模式解析文件
        if mode == 'forward':
            # 解析 XMind 文件
            parser = XMindParser(str(filepath), temp_dir=str(file_manager.base_temp_dir))
            document = parser.parse()
            
            # 获取 sheet 信息
            sheets = []
            for i, sheet in enumerate(document.sheets):
                sheets.append({
                    'index': i,
                    'title': sheet.title or f'Sheet {i+1}',
                    'node_count': len(parser.get_flat_list(i))
                })
            
            return jsonify({
                'success': True,
                'filename': filename,
                'filepath': str(filepath),
                'sheets': sheets,
                'sheet_count': len(sheets)
            })
        else:
            # 反向模式，不需要解析文件，只需要保存
            return jsonify({
                'success': True,
                'filename': filename,
                'filepath': str(filepath),
                'sheets': [],
                'sheet_count': 0
            })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/preview', methods=['POST'])
def preview_file():
    """预览 XMind 文件内容"""
    try:
        filepath = request.json.get('filepath')
        sheet_index = request.json.get('sheet_index', 0)
        
        if not filepath or not Path(filepath).exists():
            return jsonify({'error': '文件不存在'}), 400
        
        # 解析文件
        parser = XMindParser(filepath, temp_dir=str(file_manager.base_temp_dir))
        document = parser.parse()
        
        # 获取指定 sheet 的内容
        data_list = parser.get_flat_list(sheet_index=sheet_index)
        
        # 只返回前 100 个节点用于预览
        preview_data = data_list[:100]
        
        return jsonify({
            'success': True,
            'nodes': preview_data,
            'total_nodes': len(data_list),
            'displayed_nodes': len(preview_data)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/convert', methods=['POST'])
def convert_file():
    """转换文件"""
    from src.utils.monitoring import track_conversion
    try:
        data = request.json
        filepath = data.get('filepath')
        output_format = data.get('format', 'md')
        sheet_indices = data.get('sheets', [0])
        export_all_sheets = data.get('export_all_sheets', False)
        
        if not filepath or not Path(filepath).exists():
            return jsonify({'error': '文件不存在'}), 400
        
        # 解析文件
        parser = XMindParser(filepath, temp_dir=str(file_manager.base_temp_dir))
        document = parser.parse()
        
        # 确定要转换的 sheets
        if export_all_sheets:
            sheet_indices = list(range(len(document.sheets)))
        
        # 创建输出目录
        output_base = config.output_folder / Path(filepath).stem
        output_base.mkdir(parents=True, exist_ok=True)
        
        # 判断是否为单个 sheet（用于决定命名规则）
        single_sheet = len(document.sheets) == 1
        # 单个 sheet 时使用上传文件名，多个 sheet 时使用 sheet 名称
        base_filename = Path(filepath).stem if single_sheet else None
        
        results = []
        
        # 根据格式选择导出器
        for sheet_idx in sheet_indices:
            sheet = document.get_sheet(sheet_idx)
            if not sheet:
                continue
            
            # 命名规则：单个 sheet 用文件名，多个 sheet 用 sheet 名称
            if single_sheet:
                sheet_name = base_filename
            else:
                sheet_name = sheet.title or f'Sheet_{sheet_idx+1}'
            
            if output_format in ['md', 'all']:
                exporter = MarkdownExporter(document, file_manager)
                output_dir = output_base / 'md'
                output_path = output_dir / f"{sheet_name}.md"
                _conv_start = time.time()
                try:
                    exporter.export(output_path, sheet_index=sheet_idx)
                    track_conversion('md', time.time() - _conv_start, success=True)
                except Exception:
                    track_conversion('md', time.time() - _conv_start, success=False)
                    raise
                results.append({
                    'sheet': sheet_name,
                    'format': 'md',
                    'path': str(output_path),
                    'download_url': f'/api/download?path={output_path.as_posix()}'
                })
            
            if output_format in ['docx', 'all']:
                exporter = DocxExporter(document, file_manager)
                output_dir = output_base / 'docx'
                output_path = output_dir / f"{sheet_name}.docx"
                _conv_start = time.time()
                try:
                    exporter.export(output_path, sheet_index=sheet_idx)
                    track_conversion('docx', time.time() - _conv_start, success=True)
                except Exception:
                    track_conversion('docx', time.time() - _conv_start, success=False)
                    raise
                results.append({
                    'sheet': sheet_name,
                    'format': 'docx',
                    'path': str(output_path),
                    'download_url': f'/api/download?path={output_path.as_posix()}'
                })
            
            if output_format in ['outline', 'all']:
                exporter = OutlineExporter(document, file_manager)
                output_dir = output_base / 'outline'
                output_path = output_dir / f"{sheet_name}.txt"
                _conv_start = time.time()
                try:
                    exporter.export(output_path, sheet_index=sheet_idx)
                    track_conversion('outline', time.time() - _conv_start, success=True)
                except Exception:
                    track_conversion('outline', time.time() - _conv_start, success=False)
                    raise
                results.append({
                    'sheet': sheet_name,
                    'format': 'outline',
                    'path': str(output_path),
                    'download_url': f'/api/download?path={output_path.as_posix()}'
                })
        
        # 创建下载包
        download_url = None
        if len(results) > 0:
            output_base_abs = output_base.resolve()
            zip_path = file_manager.create_download_package(output_base_abs, Path(filepath).stem)
            download_url = f'/api/download?path={zip_path.as_posix()}'
        
        return jsonify({
            'success': True,
            'results': results,
            'download_url': download_url,
            'output_dir': str(output_base)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/reverse_convert', methods=['POST'])
def reverse_convert():
    """反向转换（MD/Word/Outline -> XMind）"""
    try:
        data = request.json
        filepath = data.get('filepath')
        source_format = data.get('source_format', 'md')  # md, docx, outline
        output_path = data.get('output_path')
        
        if not filepath or not Path(filepath).exists():
            return jsonify({'error': '源文件不存在'}), 400
        
        # 根据格式选择导入器
        if source_format == 'md':
            importer = MarkdownImporter(filepath)
        elif source_format == 'docx':
            importer = DocxImporter(filepath)
        elif source_format == 'outline':
            importer = OutlineImporter(filepath)
        else:
            return jsonify({'error': f'不支持的源格式: {source_format}'}), 400
        
        # 解析源文件
        document = importer.parse()
        
        # 确定输出路径
        if not output_path:
            output_path = config.output_folder / f"{Path(filepath).stem}.xmind"
        else:
            output_path = Path(output_path)
        
        # 导出为 XMind
        exporter = XMindExporter(document, file_manager)
        result_path = exporter.export(output_path)
        
        return jsonify({
            'success': True,
            'message': '反向转换成功',
            'output_path': str(result_path),
            'download_url': f'/api/download?path={result_path.as_posix()}'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/download')
def download_file():
    """下载文件"""
    try:
        path = request.args.get('path')
        
        if not path:
            return jsonify({'error': '未指定文件路径'}), 400
        
        # 将路径转换为 Path 对象
        path_obj = Path(path)
        
        # 如果是相对路径，尝试相对于项目根目录解析
        if not path_obj.is_absolute():
            path_obj = config.project_root / path_obj
        
        # 确保路径存在
        if not path_obj.exists():
            return jsonify({'error': f'文件不存在: {path_obj}'}), 404
        
        # 确保是文件而不是目录
        if not path_obj.is_file():
            return jsonify({'error': '指定路径不是文件'}), 400
        
        # 安全检查：确保路径在项目目录内
        try:
            path_resolved = path_obj.resolve()
            path_resolved.relative_to(config.project_root.resolve())
        except ValueError:
            return jsonify({'error': '非法文件路径'}), 403
        
        return send_file(str(path_obj), as_attachment=True)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def _get_file_info(path_obj, base_dir):
    """获取文件/目录信息"""
    stat = path_obj.stat()
    size = stat.st_size
    
    try:
        rel_path = str(path_obj.relative_to(base_dir))
    except ValueError:
        rel_path = path_obj.name
    
    if path_obj.is_dir():
        # 计算目录大小
        try:
            size = sum(f.stat().st_size for f in path_obj.rglob('*') if f.is_file())
            file_count = sum(1 for _ in path_obj.rglob('*') if _.is_file())
        except Exception:
            size = 0
            file_count = 0
    else:
        file_count = 1
    
    return {
        'name': path_obj.name,
        'path': str(path_obj),
        'relative_path': rel_path,
        'is_dir': path_obj.is_dir(),
        'size': size,
        'size_human': _format_size(size),
        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        'file_count': file_count
    }


@app.route('/api/list_dir')
def list_dir():
    """列出指定目录的内容（用于文件浏览器）"""
    try:
        dir_path = request.args.get('path', '')
        browse_type = request.args.get('type', 'output')  # 'output' or 'temp'
        
        # 确定根目录
        if browse_type == 'temp':
            root_dir = config.temp_folder
        else:
            root_dir = config.output_folder
        
        # 如果未指定路径，列出根目录
        if not dir_path:
            target_dir = root_dir
        else:
            target_dir = Path(dir_path)
            # 安全检查：确保路径在根目录内
            try:
                target_dir.resolve().relative_to(root_dir.resolve())
            except ValueError:
                return jsonify({'error': '非法路径'}), 403
        
        if not target_dir.exists() or not target_dir.is_dir():
            return jsonify({'error': '目录不存在'}), 404
        
        # 列出目录内容
        items = []
        total_size = 0
        file_count = 0
        
        for item in target_dir.iterdir():
            try:
                file_info = _get_file_info(item, root_dir)
                items.append(file_info)
                # 统计文件数量和大小
                if file_info['is_dir']:
                    file_count += file_info.get('file_count', 0)
                else:
                    file_count += 1
                total_size += file_info['size']
            except Exception as e:
                print(f"获取文件信息失败 {item}: {e}")
        
        # 按类型排序（目录在前）和修改时间排序
        items.sort(key=lambda x: (not x['is_dir'], x['modified']), reverse=True)
        
        return jsonify({
            'success': True,
            'current_path': str(target_dir),
            'parent_path': str(target_dir.parent) if target_dir != root_dir else None,
            'root_dir': str(root_dir),
            'items': items,
            'stats': {
                'count': file_count,
                'size': total_size,
                'size_human': _format_size(total_size)
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/list_outputs')
def list_outputs():
    """列出所有输出文件（递归）"""
    try:
        output_dir = config.output_folder
        files = []
        total_size = 0
        total_count = 0
        
        if output_dir.exists():
            # 递归遍历所有文件和目录
            for item in output_dir.rglob('*'):
                try:
                    file_info = _get_file_info(item, output_dir)
                    total_size += file_info['size']
                    total_count += file_info['file_count']
                    files.append(file_info)
                except Exception as e:
                    print(f"获取输出文件信息失败 {item}: {e}")
        
        # 按修改时间排序（最新的在前）
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'success': True,
            'files': files,
            'total_count': total_count,
            'total_size': total_size,
            'total_size_human': _format_size(total_size)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    """清理临时文件"""
    try:
        # 检查是否为强制清理
        force = request.json.get('force', False) if request.is_json else False
        
        if force:
            cleaned = file_manager.cleanup_temp(force=True)
        else:
            cleaned = file_manager.cleanup_temp()
        
        return jsonify({
            'success': True, 
            'message': f'已清理 {len(cleaned)} 个临时文件',
            'cleaned_files': cleaned
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete_output', methods=['POST'])
def delete_output():
    """删除输出文件或目录"""
    try:
        data = request.json
        path = data.get('path')
        
        if not path:
            return jsonify({'error': '未指定路径'}), 400
        
        # 将路径转换为 Path 对象
        path_obj = Path(path)
        
        # 如果是相对路径，尝试相对于输出目录解析
        if not path_obj.is_absolute():
            path_obj = config.output_folder / path_obj
        
        # 确保路径存在
        if not path_obj.exists():
            return jsonify({'error': f'文件或目录不存在: {path_obj}'}), 404
        
        # 安全检查：确保路径在输出目录内
        try:
            path_resolved = path_obj.resolve()
            path_resolved.relative_to(config.output_folder.resolve())
        except ValueError:
            return jsonify({'error': '非法文件路径'}), 403
        
        # 删除文件或目录
        if path_obj.is_file():
            path_obj.unlink()
            msg = f'已删除文件: {path_obj.name}'
        elif path_obj.is_dir():
            import shutil
            shutil.rmtree(str(path_obj))
            msg = f'已删除目录: {path_obj.name}'
        
        return jsonify({
            'success': True,
            'message': msg
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete_temp', methods=['POST'])
def delete_temp():
    """删除临时文件或目录"""
    try:
        data = request.json
        path = data.get('path')
        
        if not path:
            return jsonify({'error': '未指定路径'}), 400
        
        # 将路径转换为 Path 对象
        path_obj = Path(path)
        
        # 如果是相对路径，尝试相对于临时目录解析
        if not path_obj.is_absolute():
            path_obj = config.temp_folder / path_obj
        
        # 确保路径存在
        if not path_obj.exists():
            return jsonify({'error': f'文件或目录不存在: {path_obj}'}), 404
        
        # 安全检查：确保路径在临时目录内
        try:
            path_resolved = path_obj.resolve()
            path_resolved.relative_to(config.temp_folder.resolve())
        except ValueError:
            return jsonify({'error': '非法文件路径'}), 403
        
        # 删除文件或目录
        if path_obj.is_file():
            path_obj.unlink()
            msg = f'已删除文件: {path_obj.name}'
        elif path_obj.is_dir():
            import shutil
            shutil.rmtree(str(path_obj))
            msg = f'已删除目录: {path_obj.name}'
        
        return jsonify({
            'success': True,
            'message': msg
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/temp_status')
def temp_status():
    """获取临时文件状态（递归）"""
    try:
        temp_dir = config.temp_folder
        files = []
        total_size = 0
        total_count = 0
        
        if temp_dir.exists():
            # 递归遍历所有文件和目录
            for item in temp_dir.rglob('*'):
                try:
                    file_info = _get_file_info(item, temp_dir)
                    total_size += file_info['size']
                    total_count += file_info['file_count']
                    files.append(file_info)
                except Exception as e:
                    print(f"获取文件信息失败 {item}: {e}")
        
        # 按修改时间排序（最新的在前）
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'success': True,
            'files': files,
            'total_count': total_count,
            'total_size': total_size,
            'total_size_human': _format_size(total_size),
            'temp_dir': str(temp_dir)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def _format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


if __name__ == '__main__':
    print(f"项目根目录: {config.project_root}")
    print(f"上传目录: {config.upload_folder}")
    print(f"输出目录: {config.output_folder}")
    print(f"临时目录: {config.temp_folder}")
    print(f"配置文件: {config.config_file}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
