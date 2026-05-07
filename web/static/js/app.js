// 全局变量
var currentFilepath = null;
var sheetData = [];
var currentMode = 'forward';
var currentOutputPath = '';
var currentTempPath = '';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeUpload();
    loadConfig();
    
    // 点击弹窗外部关闭弹窗
    document.querySelectorAll('.modal').forEach(function(modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.style.display = 'none';
            }
        });
    });
});

// ========= 工具函数 =========

function showLoading() {
    var el = document.getElementById('loadingOverlay');
    if (el) el.style.display = 'flex';
}

function hideLoading() {
    var el = document.getElementById('loadingOverlay');
    if (el) el.style.display = 'none';
}

function showError(message) {
    alert('错误: ' + message);
}

function showMessage(message, type) {
    var msg = document.createElement('div');
    msg.className = 'message-toast ' + type;
    var icon = type === 'success' ? 'check-circle' : 'exclamation-circle';
    msg.innerHTML = '<i class="fas fa-' + icon + '"></i> ' + message;
    document.body.appendChild(msg);
    setTimeout(function() {
        msg.style.opacity = '0';
        setTimeout(function() { msg.remove(); }, 300);
    }, 3000);
}

function downloadFile(path) {
    var url = '/api/download?path=' + encodeURIComponent(path);
    window.open(url, '_blank');
}

// ========= 模式切换 =========

function switchMode(mode, evt) {
    currentMode = mode;
    
    // 更新标签样式
    document.querySelectorAll('.tab-btn').forEach(function(btn) {
        btn.classList.remove('active');
    });
    if (evt && evt.target) {
        var clickedBtn = evt.target.closest('.tab-btn');
        if (clickedBtn) {
            clickedBtn.classList.add('active');
        }
    }
    
    // 根据模式更新文件输入框的接受类型和提示文本
    var fileInput = document.getElementById('fileInput');
    var uploadHint = document.getElementById('uploadHint');
    if (mode === 'forward') {
        fileInput.accept = '.xmind';
        uploadHint.textContent = '拖拽 XMind 文件到此处，或点击选择文件';
    } else {
        fileInput.accept = '.md,.docx,.txt';
        uploadHint.textContent = '拖拽 Markdown/Word/大纲 文件到此处，或点击选择文件';
    }
    
    // 重置文件状态
    resetFileState();
    
    // 重置状态
    currentFilepath = null;
}

function resetFileState() {
    // 显示上传区域
    document.getElementById('uploadArea').style.display = 'block';
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('sheetSection').style.display = 'none';
    document.getElementById('formatSection').style.display = 'none';
    document.getElementById('convertSection').style.display = 'none';
    document.getElementById('reverseSection').style.display = 'none';
    document.getElementById('previewSection').style.display = 'none';
    document.getElementById('resultSection').style.display = 'none';
    
    // 根据当前模式显示正确的区域
    if (currentMode === 'reverse') {
        document.getElementById('reverseSection').style.display = 'block';
    }
}
// ========= 配置管理 ==========

function showConfigModal() {
    document.getElementById('configModal').style.display = 'flex';
    loadConfig();
}

function closeConfigModal() {
    document.getElementById('configModal').style.display = 'none';
}

function loadConfig() {
    fetch('/api/config')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success && data.config) {
                var policy = data.config.temp_policy;
                document.getElementById('autoCleanup').checked = policy.auto_cleanup;
                document.getElementById('retentionHours').value = policy.retention_hours;
                document.getElementById('maxFileCount').value = policy.max_file_count;
                document.getElementById('maxFileSize').value = policy.max_file_size_mb;
                document.getElementById('cleanupInterval').value = policy.cleanup_interval_minutes;
                document.getElementById('cleanupOnStartup').checked = policy.cleanup_on_startup;
                document.getElementById('maxUploadSize').value = data.config.max_upload_size_mb;
            }
        })
        .catch(function(error) { console.error('加载配置失败:', error); });
}

function saveConfig() {
    var config = {
        temp_policy: {
            auto_cleanup: document.getElementById('autoCleanup').checked,
            retention_hours: parseInt(document.getElementById('retentionHours').value),
            max_file_count: parseInt(document.getElementById('maxFileCount').value),
            max_file_size_mb: parseInt(document.getElementById('maxFileSize').value),
            cleanup_interval_minutes: parseInt(document.getElementById('cleanupInterval').value),
            cleanup_on_startup: document.getElementById('cleanupOnStartup').checked
        },
        max_upload_size_mb: parseInt(document.getElementById('maxUploadSize').value)
    };
    
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data.success) {
            showMessage('设置已保存', 'success');
            closeConfigModal();
        } else {
            showMessage('保存失败: ' + data.error, 'error');
        }
    })
    .catch(function(error) { showMessage('保存失败: ' + error, 'error'); });
}
// ========= 文件浏览器（递归目录浏览）==========

function browseOutput(path) {
    currentOutputPath = path || '';
    var url = '/api/list_dir?type=output';
    if (path) {
        url += '&path=' + encodeURIComponent(path);
    }
    
    fetch(url)
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success) {
                renderFileBrowser('output', data);
            } else {
                showMessage('浏览失败: ' + data.error, 'error');
            }
        })
        .catch(function(error) {
            showMessage('浏览失败: ' + error, 'error');
        });
}

function browseTemp(path) {
    currentTempPath = path || '';
    var url = '/api/list_dir?type=temp';
    if (path) {
        url += '&path=' + encodeURIComponent(path);
    }
    
    fetch(url)
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success) {
                renderFileBrowser('temp', data);
            } else {
                showMessage('浏览失败: ' + data.error, 'error');
            }
        })
        .catch(function(error) {
            showMessage('浏览失败: ' + error, 'error');
        });
}

function renderFileBrowser(type, data) {
    var listId = type === 'output' ? 'outputFilesList' : 'tempFilesList';
    var statsId = type === 'output' ? 'outputStats' : 'tempStats';
    var countId = type === 'output' ? 'outputFileCount' : 'tempFileCount';
    var sizeId = type === 'output' ? 'outputTotalSize' : 'tempTotalSize';
    
    // 更新统计信息
    if (data.stats) {
        document.getElementById(countId).textContent = data.stats.count;
        document.getElementById(sizeId).textContent = data.stats.size_human;
    }
    
    var list = document.getElementById(listId);
    
    // 生成面包屑导航
    var breadcrumb = generateBreadcrumb(type, data.current_path, data.root_dir);
    
    // 生成返回上级按钮
    var backBtn = '';
    if (data.parent_path) {
        backBtn = '<div class="file-browser-item back-item" onclick="goBack(\'' + type + '\')">' +
            '<i class="fas fa-arrow-left"></i> .. (返回上级)</div>';
    }
    
    // 生成文件列表
    var html = breadcrumb + backBtn;
    
    if (!data.items || data.items.length === 0) {
        html += '<p class="placeholder-text">此目录为空</p>';
        list.innerHTML = html;
        return;
    }
    
    data.items.forEach(function(item) {
        var icon = item.is_dir ? '<i class="fas fa-folder"></i>' : '<i class="fas fa-file"></i>';
        var clickAction = item.is_dir ? 'browse' + (type.charAt(0).toUpperCase() + type.slice(1)) + '(\'' + item.path.replace(/\\/g, '\\\\') + '\')' : '';
        var downloadBtn = '';
        var deleteBtn = '<button class="btn btn-xs btn-danger" onclick="event.stopPropagation(); deleteFile(\'' + type + '\', \'' + item.path.replace(/\\/g, '\\\\') + '\', \'' + item.name + '\')"><i class="fas fa-trash"></i></button>';
        
        if (!item.is_dir) {
            downloadBtn = '<button class="btn btn-xs btn-primary" onclick="event.stopPropagation(); downloadFile(\'' + item.path.replace(/\\/g, '\\\\') + '\')"><i class="fas fa-download"></i></button>';
        }
        
        html += '<div class="file-browser-item ' + (item.is_dir ? 'dir-item' : 'file-item') + '" ' + (clickAction ? 'onclick="' + clickAction + '"' : '') + '>' +
            '<span class="file-icon">' + icon + '</span>' +
            '<span class="file-name">' + item.name + '</span>' +
            '<span class="file-meta">' + (item.is_dir ? '目录' : item.size_human) + '</span>' +
            '<span class="file-actions-inline">' +
                downloadBtn +
                deleteBtn +
            '</span>' +
        '</div>';
    });
    
    list.innerHTML = html;
}
function generateBreadcrumb(type, currentPath, rootDir) {
    if (!currentPath || currentPath === rootDir) {
        return '<div class="breadcrumb"><span class="breadcrumb-item active">根目录</span></div>';
    }
    
    var parts = currentPath.substring(rootDir.length).split('\\').filter(function(p) { return p; });
    var html = '<div class="breadcrumb"><span class="breadcrumb-item" onclick="browse' + 
        (type.charAt(0).toUpperCase() + type.slice(1)) + '(\'\')">根目录</span>';
    
    var pathAccum = rootDir;
    parts.forEach(function(part, index) {
        pathAccum += '\\' + part;
        if (index === parts.length - 1) {
            html += '<span class="breadcrumb-separator">/</span><span class="breadcrumb-item active">' + part + '</span>';
        } else {
            var path = pathAccum;
            html += '<span class="breadcrumb-separator">/</span><span class="breadcrumb-item" onclick="browse' + 
                (type.charAt(0).toUpperCase() + type.slice(1)) + '(\'' + path + '\')">' + part + '</span>';
        }
    });
    html += '</div>';
    
    return html;
}

function goBack(type) {
    if (type === 'output') {
        var current = currentOutputPath || '';
        if (!current) return;
        var parent = current.substring(0, current.lastIndexOf('\\'));
        browseOutput(parent || '');
    } else {
        var current = currentTempPath || '';
        if (!current) return;
        var parent = current.substring(0, current.lastIndexOf('\\'));
        browseTemp(parent || '');
    }
}

function deleteFile(type, path, name) {
    if (!confirm('确定要删除 ' + name + ' 吗？')) {
        return;
    }
    
    var apiUrl = type === 'output' ? '/api/delete_output' : '/api/delete_temp';
    
    showLoading();
    fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: path })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        hideLoading();
        if (data.success) {
            showMessage(data.message, 'success');
            // 刷新当前目录
            if (type === 'output') {
                browseOutput(currentOutputPath);
            } else {
                browseTemp(currentTempPath);
            }
        } else {
            showMessage('删除失败: ' + (data.error || '未知错误'), 'error');
        }
    })
    .catch(function(error) {
        hideLoading();
        showMessage('删除失败: ' + error, 'error');
    });
}
// ========= 输出文件管理 ==========

function showOutputFilesModal() {
    document.getElementById('outputFilesModal').style.display = 'flex';
    currentOutputPath = '';
    browseOutput('');
}

function closeOutputFilesModal() {
    document.getElementById('outputFilesModal').style.display = 'none';
}

// ========= 临时文件管理 ==========

function showTempFilesModal() {
    document.getElementById('tempFilesModal').style.display = 'flex';
    currentTempPath = '';
    browseTemp('');
}

function closeTempFilesModal() {
    document.getElementById('tempFilesModal').style.display = 'none';
}

// ========= 清理临时文件 ==========

function cleanupTempFiles() {
    if (!confirm('确定要清理临时文件吗？\n\n点击"确定"仅清理过期文件\n点击"取消"后可以选择强制清理所有文件')) {
        // 用户取消，询问是否强制清理
        if (confirm('是否强制清理所有临时文件（包括未过期的）？')) {
            forceCleanup();
        }
        return;
    }
    
    // 用户确认，执行普通清理
    doCleanup(false);
}

function forceCleanup() {
    showLoading();
    fetch('/api/cleanup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: true })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        hideLoading();
        if (data.success) {
            showMessage(data.message, 'success');
            browseTemp('');
        } else {
            showMessage('清理失败: ' + data.error, 'error');
        }
    })
    .catch(function(error) {
        hideLoading();
        showMessage('清理失败: ' + error, 'error');
    });
}

function doCleanup(force) {
    showLoading();
    var options = {
        method: 'POST'
    };
    
    if (force) {
        options.headers = { 'Content-Type': 'application/json' };
        options.body = JSON.stringify({ force: true });
    }
    
    fetch('/api/cleanup', options)
    .then(function(response) { return response.json(); })
    .then(function(data) {
        hideLoading();
        if (data.success) {
            showMessage(data.message, 'success');
            browseTemp('');
        } else {
            showMessage('清理失败: ' + data.error, 'error');
        }
    })
    .catch(function(error) {
        hideLoading();
        showMessage('清理失败: ' + error, 'error');
    });
}
// ========= 文件上传 ==========

function initializeUpload() {
    var uploadArea = document.getElementById('uploadArea');
    var fileInput = document.getElementById('fileInput');
    
    // 点击上传区域触发文件选择
    uploadArea.addEventListener('click', function(e) {
        if (e.target.tagName !== 'BUTTON') {
            fileInput.click();
        }
    });
    
    // 文件选择事件
    fileInput.addEventListener('change', function(e) {
        if (this.files.length > 0) {
            uploadFile(this.files[0]);
        }
    });
    
    // 拖拽上传事件
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.style.borderColor = '#764ba2';
        this.style.background = '#e8ebff';
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.style.borderColor = '#667eea';
        this.style.background = '#f8f9ff';
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.style.borderColor = '#667eea';
        this.style.background = '#f8f9ff';
        
        var files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFile(files[0]);
        }
    });
}

function uploadFile(file) {
    // 验证文件类型
    var allowedExtensions;
    if (currentMode === 'forward') {
        allowedExtensions = ['.xmind'];
    } else {
        allowedExtensions = ['.md', '.docx', '.txt'];
    }
    
    var fileName = file.name.toLowerCase();
    var isValid = false;
    for (var i = 0; i < allowedExtensions.length; i++) {
        if (fileName.endsWith(allowedExtensions[i])) {
            isValid = true;
            break;
        }
    }
    
    if (!isValid) {
        var formatNames = currentMode === 'forward' ? 'XMind (.xmind)' : 'Markdown (.md)、Word (.docx) 或 大纲 (.txt)';
        showMessage('不支持的文件格式，请上传 ' + formatNames + ' 文件', 'error');
        return;
    }
    
    // 显示加载动画
    showLoading();
    
    // 创建表单数据
    var formData = new FormData();
    formData.append('file', file);
    formData.append('mode', currentMode);
    
    // 发送上传请求
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        hideLoading();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // 保存文件路径
        currentFilepath = data.filepath;
        sheetData = data.sheets || [];
        
        // 显示文件信息
        displayFileInfo(data);
        
        if (currentMode === 'forward') {
            // 显示 Sheet 选择
            displaySheetSelection(data.sheets);
            
            // 显示格式选择
            document.getElementById('formatSection').style.display = 'block';
            
            // 显示转换按钮
            document.getElementById('convertSection').style.display = 'block';
            
            // 显示预览区域
            displayPreviewSection(data.sheets);
        } else {
            // 反向模式，显示反向转换按钮
            document.getElementById('reverseSection').style.display = 'block';
        }
        
    })
    .catch(function(error) {
        hideLoading();
        showError('上传失败: ' + error.message);
    });
}

function displayFileInfo(data) {
    document.getElementById('uploadArea').style.display = 'none';
    document.getElementById('fileInfo').style.display = 'block';
    document.getElementById('fileName').textContent = data.filename;
    
    if (data.sheet_count !== undefined) {
        document.getElementById('sheetCount').textContent = data.sheet_count;
    } else {
        document.getElementById('sheetCount').textContent = '1';
    }
}
function displaySheetSelection(sheets) {
    var sheetSection = document.getElementById('sheetSection');
    var sheetList = document.getElementById('sheetList');
    
    sheetSection.style.display = 'block';
    sheetList.innerHTML = '';
    
    sheets.forEach(function(sheet, index) {
        var sheetItem = document.createElement('div');
        sheetItem.className = 'sheet-item selected';
        sheetItem.innerHTML = '<input type="checkbox" id="sheet_' + index + '" checked>' +
            '<label for="sheet_' + index + '">' +
                '<strong>' + sheet.title + '</strong>' +
                '<span style="color: #999; margin-left: 10px;">(' + sheet.node_count + ' 个节点)</span>' +
            '</label>';
        sheetList.appendChild(sheetItem);
    });
}

function displayPreviewSection(sheets) {
    var previewSection = document.getElementById('previewSection');
    var previewSheetSelect = document.getElementById('previewSheetSelect');
    
    previewSection.style.display = 'block';
    previewSheetSelect.innerHTML = '';
    
    sheets.forEach(function(sheet, index) {
        var option = document.createElement('option');
        option.value = index;
        option.textContent = sheet.title;
        previewSheetSelect.appendChild(option);
    });
    
    // 自动预览第一个 Sheet
    previewFile();
}

// ========= 文件预览 ==========

function previewFile() {
    var sheetIndex = document.getElementById('previewSheetSelect').value;
    
    if (!currentFilepath) {
        return;
    }
    
    showLoading();
    
    fetch('/api/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            filepath: currentFilepath,
            sheet_index: parseInt(sheetIndex)
        })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        hideLoading();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        displayPreview(data);
    })
    .catch(function(error) {
        hideLoading();
        showError('预览失败: ' + error.message);
    });
}

function displayPreview(data) {
    var previewContent = document.getElementById('previewContent');
    previewContent.innerHTML = '';
    
    if (data.nodes.length === 0) {
        previewContent.innerHTML = '<p class="placeholder-text">该 Sheet 没有内容</p>';
        return;
    }
    
    data.nodes.forEach(function(node) {
        var nodeDiv = document.createElement('div');
        nodeDiv.className = 'preview-node';
        nodeDiv.style.marginLeft = (node.level * 20) + 'px';
        
        var html = '<div class="node-title">' + '├─ '.repeat(node.level) + node.title + '</div>';
        
        if (node.notes) {
            html += '<div class="node-notes">备注: ' + node.notes + '</div>';
        }
        
        if (node.labels && node.labels.length > 0) {
            html += '<div class="node-labels">';
            node.labels.forEach(function(label) {
                html += '<span class="label">' + label + '</span>';
            });
            html += '</div>';
        }
        
        nodeDiv.innerHTML = html;
        previewContent.appendChild(nodeDiv);
    });
    
    if (data.total_nodes > data.displayed_nodes) {
        var moreDiv = document.createElement('div');
        moreDiv.className = 'placeholder-text';
        moreDiv.textContent = '... 还有 ' + (data.total_nodes - data.displayed_nodes) + ' 个节点未显示';
        previewContent.appendChild(moreDiv);
    }
}
// =========== 文件转换 ==========

function convertFile() {
    if (!currentFilepath) {
        showError('请先上传文件');
        return;
    }
    
    // 获取选中的 Sheet
    var selectedSheets = [];
    var sheetCheckboxes = document.querySelectorAll('#sheetList input[type="checkbox"]:checked');
    sheetCheckboxes.forEach(function(cb) {
        selectedSheets.push(parseInt(cb.id.replace('sheet_', '')));
    });
    
    if (selectedSheets.length === 0) {
        showError('请至少选择一个 Sheet');
        return;
    }
    
    // 获取选中的格式
    var selectedFormats = [];
    var formatCheckboxes = document.querySelectorAll('#formatSection input[type="checkbox"]:checked');
    formatCheckboxes.forEach(function(cb) {
        selectedFormats.push(cb.value);
    });
    
    if (selectedFormats.length === 0) {
        showError('请至少选择一种导出格式');
        return;
    }
    
    // 显示加载动画
    showLoading();
    
    // 发送转换请求
    fetch('/api/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            filepath: currentFilepath,
            sheets: selectedSheets,
            format: selectedFormats.length === 1 ? selectedFormats[0] : 'all',
            export_all_sheets: selectedSheets.length === sheetData.length
        })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        hideLoading();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // 显示结果
        displayResults(data);
    })
    .catch(function(error) {
        hideLoading();
        showError('转换失败: ' + error.message);
    });
}

function displayResults(data) {
    var resultSection = document.getElementById('resultSection');
    var resultContent = document.getElementById('resultContent');
    var downloadActions = document.getElementById('downloadActions');
    
    resultSection.style.display = 'block';
    resultContent.innerHTML = '';
    downloadActions.innerHTML = '';
    
    if (data.results && data.results.length > 0) {
        data.results.forEach(function(result) {
            var resultItem = document.createElement('div');
            resultItem.className = 'result-item';
            resultItem.innerHTML = '<h3><i class="fas fa-check-circle"></i> ' + result.sheet + '</h3>' +
                '<p><strong>格式:</strong> ' + result.format.toUpperCase() + '</p>' +
                '<p><strong>路径:</strong> ' + result.path + '</p>';
            resultContent.appendChild(resultItem);
        });
        
        // 添加下载按钮
        if (data.download_url) {
            var downloadBtn = document.createElement('a');
            downloadBtn.href = data.download_url;
            downloadBtn.className = 'download-btn';
            downloadBtn.innerHTML = '<i class="fas fa-download"></i> 下载全部 (ZIP)';
            downloadActions.appendChild(downloadBtn);
        }
        
        // 添加单个文件下载链接
        data.results.forEach(function(result) {
            var downloadBtn = document.createElement('a');
            downloadBtn.href = result.download_url;
            downloadBtn.className = 'download-btn';
            downloadBtn.innerHTML = '<i class="fas fa-file-download"></i> 下载 ' + result.sheet + ' (' + result.format.toUpperCase() + ')';
            downloadActions.appendChild(downloadBtn);
        });
    }
}

// =========== 反向转换 ==========

function reverseConvert() {
    if (!currentFilepath) {
        showMessage('请先上传文件', 'error');
        return;
    }
    
    // 获取选中的源格式
    var sourceFormat = document.querySelector('input[name="sourceFormat"]:checked').value;
    
    showLoading();
    
    fetch('/api/reverse_convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            filepath: currentFilepath,
            source_format: sourceFormat
        })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        hideLoading();
        if (data.success) {
            showMessage(data.message, 'success');
            
            // 显示结果
            document.getElementById('resultSection').style.display = 'block';
            document.getElementById('resultContent').innerHTML = '<p><i class="fas fa-check-circle"></i> ' + data.message + '</p><p><strong>输出文件:</strong> ' + data.output_path + '</p>';
            
            document.getElementById('downloadActions').innerHTML = '<a href="' + data.download_url + '" class="download-btn"><i class="fas fa-download"></i> 下载 XMind 文件</a>';
        } else {
            showMessage('转换失败: ' + data.error, 'error');
        }
    })
    .catch(function(error) {
        hideLoading();
        showMessage('转换失败: ' + error, 'error');
    });
}
// ========= Sheet 选择 ==========

function selectAllSheets() {
    var checkboxes = document.querySelectorAll('#sheetList input[type="checkbox"]');
    checkboxes.forEach(function(cb) {
        cb.checked = true;
        cb.parentElement.classList.add('selected');
    });
}

function deselectAllSheets() {
    var checkboxes = document.querySelectorAll('#sheetList input[type="checkbox"]');
    checkboxes.forEach(function(cb) {
        cb.checked = false;
        cb.parentElement.classList.remove('selected');
    });
}

function resetFile() {
    currentFilepath = null;
    sheetData = [];
    
    document.getElementById('uploadArea').style.display = 'block';
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('sheetSection').style.display = 'none';
    document.getElementById('formatSection').style.display = 'none';
    document.getElementById('convertSection').style.display = 'none';
    document.getElementById('reverseSection').style.display = 'none';
    document.getElementById('previewSection').style.display = 'none';
    document.getElementById('resultSection').style.display = 'none';
    
    document.getElementById('fileInput').value = '';
}

// ========= 帮助弹窗 ==========

function showHelpModal() {
    document.getElementById('helpModal').style.display = 'flex';
}

function closeHelpModal() {
    document.getElementById('helpModal').style.display = 'none';
}

// ========= 工具函数补充 ==========

// 字符串重复函数（兼容旧浏览器）
if (!String.prototype.repeat) {
    String.prototype.repeat = function(count) {
        var str = '';
        for (var i = 0; i < count; i++) {
            str += this;
        }
        return str;
    };
}

// 字符串 endsWith 兼容
if (!String.prototype.endsWith) {
    String.prototype.endsWith = function(suffix) {
        return this.indexOf(suffix, this.length - suffix.length) !== -1;
    };
}
