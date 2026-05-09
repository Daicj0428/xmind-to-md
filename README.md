# XMind to MD - XMind 转换工具

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-2.3.0-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![Prometheus](https://img.shields.io/badge/prometheus-monitoring-orange.svg)](https://prometheus.io/)

一个支持将 XMind 思维导图转换为多种格式的 Web 工具，支持 Docker 部署和 Prometheus 监控。

## 功能特性

- 📤 **拖拽上传**：支持拖拽上传 XMind 文件
- 👁️ **实时预览**：上传后自动预览文件结构
- 📑 **多 Sheet 支持**：可选择导出单个或所有 Sheet
- 📄 **多格式导出**：支持 Markdown、Word、大纲格式
- 🖼️ **图片处理**：自动提取并保存思维导图中的图片
- 📦 **打包下载**：所有导出文件打包为 ZIP 下载
- 🎨 **现代化界面**：响应式设计，支持移动端
- 📊 **Prometheus 监控**：导出 /metrics 端点供 Prometheus 采集
- 🐳️ **Docker 支持**：多阶段构建，最小化镜像大小

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/xmind-to-md.git
cd xmind-to-md
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动 Web 服务器

**方法一：使用启动脚本（推荐）**

```bash
python run_web.py
```

启动后会自动打开浏览器访问 `http://127.0.0.1:5000/`

**方法二：直接运行 Flask 应用**

```bash
python web/app.py
```

然后手动访问 `http://127.0.0.1:5000/`

### 4. 使用步骤

1. **上传文件**
   - 拖拽 XMind 文件到上传区域，或点击“选择文件”按钮
   - 支持 `.xmind` 格式文件
2. **选择 Sheet**
   - 上传后会显示文件中的所有 Sheet
   - 可选择一个或多个 Sheet 进行导出
   - 支持全选/取消全选
3. **选择导出格式**
   - Markdown (.md)
   - Word (.docx)
   - 大纲 (.txt)
   - 可同时选择多种格式
4. **预览内容**
   - 选择要预览的 Sheet
   - 查看文件结构和内容
5. **开始转换**
   - 点击“开始转换”按钮
   - 等待转换完成
6. **下载结果**
   - 转换完成后显示下载链接
   - 可下载单个文件或打包下载所有文件

## Docker 部署

### 构建镜像

```bash
docker build -t xmind-to-md:latest .
```

### 运行容器

```bash
# 基本运行（默认端口 30000）
docker run -p 30000:30000 xmind-to-md:latest

# 自定义端口（Docker/K8s 场景）
docker run -p 30001:30001 -e PORT=30001 xmind-to-md:latest
```

### Kubernetes 部署

#### 基础部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: xmind-to-md
spec:
  replicas: 1
  selector:
    matchLabels:
      app: xmind-to-md
  template:
    metadata:
      labels:
        app: xmind-to-md
    spec:
      containers:
      - name: xmind-to-md
        image: xmind-to-md:latest
        ports:
        - containerPort: 30000
        env:
        - name: PORT
          value: "30000"
        volumeMounts:
        - name: temp-volume
          mountPath: /app/temp
        - name: output-volume
          mountPath: /app/output
      volumes:
      - name: temp-volume
        emptyDir: {}
      - name: output-volume
        emptyDir: {}
```

#### Prometheus 监控自动发现 (ServiceMonitor)

在 K8s 集群中使用 Prometheus Operator 时，创建 Service 和 ServiceMonitor 实现自动指标采集：

**1. 创建 Service**

```bash
kubectl apply -f k8s-service.yaml
```

**2. 创建 ServiceMonitor**

```bash
kubectl apply -f servicemonitor.yaml
```

**配置文件说明：**

| 文件 | 用途 |
|------|------|
| `k8s-service.yaml` | 暴露服务的 HTTP 和 metrics 端口 |
| `servicemonitor.yaml` | Prometheus Operator 自动发现配置 |

**验证监控：**

```bash
# 查看 ServiceMonitor
kubectl get servicemonitor -n monitoring

# 查看 Prometheus 目标
kubectl port-forward svc/prometheus-k8s 9090:9090 -n monitoring
# 访问 http://localhost:9090/targets 查看 xmind-to-md 是否已注册
```

## Prometheus 监控

应用暴露 `/metrics` 端点，供 Prometheus 采集指标。

### 可用指标

| 指标名称                              | 类型      | 描述                                               |
| ------------------------------------- | --------- | -------------------------------------------------- |
| `xmind_requests_total`              | Counter   | 总 HTTP 请求数（按 method、endpoint、status 分类） |
| `xmind_request_duration_seconds`    | Histogram | 请求延迟（秒）                                     |
| `xmind_uploads_total`               | Counter   | 文件上传总数（按 status: success/failed）          |
| `xmind_upload_size_bytes`           | Histogram | 上传文件大小（字节）                               |
| `xmind_conversions_total`           | Counter   | 转换任务总数（按 format、status）                  |
| `xmind_conversion_duration_seconds` | Histogram | 转换耗时（秒）                                     |
| `xmind_temp_files`                  | Gauge     | 当前临时文件数量                                   |
| `xmind_output_files`                | Gauge     | 当前输出文件数量                                   |
| `xmind_disk_usage_bytes`            | Gauge     | 磁盘使用量（字节，按 type: temp/output）           |

### Prometheus 配置示例

```yaml
scrape_configs:
  - job_name: 'xmind-to-md'
    static_configs:
      - targets: ['localhost:30000']
```

### Alertmanager 告警配置

项目提供了完整的告警规则配置，支持邮件通知。

**配置文件：**
- `prometheus.yml` - Prometheus 主配置
- `alert_rules.yml` - 告警规则定义（10 条告警规则）
- `alertmanager.yml` - 告警通知配置

**告警规则概览：**

| 告警名称 | 严重级别 | 触发条件 |
|---------|---------|---------|
| XMindServiceDown | critical | 服务宕机超过 1 分钟 |
| XMindHighLatency | warning | P99 延迟 > 5 秒 |
| XMindUploadFailureRateHigh | warning | 上传失败率 > 10% |
| XMindLargeUpload | warning | P95 文件大小 > 50MB |
| XMindConversionFailureRateHigh | critical | 转换失败率 > 5% |
| XMindConversionSlow | warning | P99 转换耗时 > 30 秒 |
| XMindTempFilesHigh | warning | 临时文件 > 1000 |
| XMindDiskSpaceLow | warning | 磁盘使用 > 10GB |
| XMindRequestSpike | warning | QPS > 100 |
| XMindNoRequests | warning | 30 分钟无请求 |

**快速启动：**

```bash
# 启动 Alertmanager
./alertmanager --config.file=alertmanager.yml

# 启动 Prometheus
./prometheus --config.file=prometheus.yml

# 查看告警
# http://localhost:9090/alerts  (Prometheus)
# http://localhost:9093          (Alertmanager)
```

### Grafana 仪表盘

项目提供了预配置的 Grafana 仪表盘文件 `grafana-dashboard.json`，可直接导入。

**导入步骤：**

1. 打开 Grafana → Dashboards → Import
2. 上传 `grafana-dashboard.json` 或复制其内容粘贴
3. 选择 Prometheus 数据源
4. 点击 Import

**仪表盘包含以下面板：**

| 面板             | 描述                                        |
| ---------------- | ------------------------------------------- |
| 请求速率 (QPS)   | 按端点统计每秒请求数                        |
| 请求延迟 (P99)   | P99 请求延迟趋势                            |
| 上传成功率       | 最近 5 分钟上传成功率（红 < 95%，绿 > 99%） |
| 转换成功率       | 按格式统计转换成功率                        |
| 总请求量 (5分钟) | 最近 5 分钟总请求数                         |
| 上传文件大小     | P50/P95 上传文件大小                        |
| 转换耗时 (P99)   | 按格式统计 P99 转换耗时                     |
| 临时文件数量     | 当前临时文件数趋势                          |
| 磁盘使用量       | 临时文件和输出文件磁盘占用                  |

**常用查询参考：**

- 请求速率：`rate(xmind_requests_total[5m])`
- P99 延迟：`histogram_quantile(0.99, rate(xmind_request_duration_seconds_bucket[5m]))`
- 上传成功率：`rate(xmind_uploads_total{status="success"}[5m]) / rate(xmind_uploads_total[5m])`
- 转换成功率：`rate(xmind_conversions_total{status="success"}[5m]) / rate(xmind_conversions_total[5m])`

## API 接口说明

### 1. 上传文件

```
POST /api/upload
Content-Type: multipart/form-data

Response:
{
    "success": true,
    "filename": "test.xmind",
    "filepath": "temp/uploads/test.xmind",
    "sheets": [...],
    "sheet_count": 2
}
```

### 2. 预览文件

```
POST /api/preview
Content-Type: application/json

Body:
{
    "filepath": "temp/uploads/test.xmind",
    "sheet_index": 0
}

Response:
{
    "success": true,
    "nodes": [...],
    "total_nodes": 100,
    "displayed_nodes": 100
}
```

### 3. 转换文件

```
POST /api/convert
Content-Type: application/json

Body:
{
    "filepath": "temp/uploads/test.xmind",
    "sheets": [0, 1],
    "format": "md",
    "export_all_sheets": false
}

Response:
{
    "success": true,
    "results": [...],
    "download_url": "/api/download?path=..."
}
```

### 4. 下载文件

```
GET /api/download?path=output/test/Sheet1.md

Response: 文件下载
```

### 5. Prometheus 指标

```
GET /metrics

Response: Prometheus 格式的指标数据
```

## 输出文件结构

转换后的文件保存在 `output/` 目录：

```
output/
├── 文件名/
│   ├── md/              # Markdown 格式
│   │   ├── Sheet1.md
│   │   └── images/
│   ├── docx/            # Word 格式
│   │   ├── Sheet1.docx
│   │   └── images/
│   └── outline/         # 大纲格式
│       ├── Sheet1.txt
│       └── images/
```

**命名规则**：

- **只有一个 Sheet**：输出文件使用上传文件名（如 `LINUX常用命令.md`）
- **多个 Sheet**：输出文件使用 Sheet 名称（如 `Sheet1.md`、`Sheet2.md`）

## 配置说明

配置文件：`config.json`

```json
{
  "temp_policy": {
    "auto_cleanup": true,
    "retention_hours": 24,
    "max_file_size_mb": 100,
    "max_file_count": 100,
    "cleanup_on_startup": true,
    "cleanup_interval_minutes": 60
  },
  "max_upload_size_mb": 100
}
```

| 配置项                                   | 描述                   | 默认值   |
| ---------------------------------------- | ---------------------- | -------- |
| `temp_policy.auto_cleanup`             | 是否自动清理临时文件   | `true` |
| `temp_policy.retention_hours`          | 文件保留时间（小时）   | `24`   |
| `temp_policy.max_file_size_mb`         | 最大文件大小（MB）     | `100`  |
| `temp_policy.max_file_count`           | 最大文件数量           | `100`  |
| `temp_policy.cleanup_on_startup`       | 启动时是否清理         | `true` |
| `temp_policy.cleanup_interval_minutes` | 清理间隔（分钟）       | `60`   |
| `max_upload_size_mb`                   | 上传文件大小限制（MB） | `100`  |

## 注意事项

1. **文件大小限制**：默认限制上传文件大小为 100MB
2. **临时文件**：上传的文件会保存在 `temp/uploads/` 目录
3. **输出文件**：转换后的文件保存在 `output/` 目录
4. **清理临时文件**：可点击“清理临时文件”按钮清理
5. **端口配置**：支持 `PORT` 环境变量（Docker/K8s 场景，默认 30000）

## 技术栈

- **后端**：Flask 2.3+
- **前端**：HTML5 + CSS3 + JavaScript (ES6+)
- **UI 框架**：Font Awesome 图标
- **核心库**：
  - `xmind`：XMind 文件解析
  - `python-docx`：Word 文档生成
  - `Pillow`：图片处理
  - `prometheus_client`：Prometheus 指标导出

## 常见问题

### 1. 上传失败

- 检查文件是否为 `.xmind` 格式
- 检查文件大小是否超过 100MB
- 检查文件是否损坏

### 2. 转换失败

- 检查 XMind 文件版本（支持 XMind 8+）
- 检查文件是否加密
- 查看浏览器控制台错误信息

### 3. 图片未显示

- 检查 XMind 文件中是否包含图片
- 检查图片是否成功提取到 `images/` 目录
- 检查 Markdown 中的图片路径是否正确（应为 `../images/图片名.png`）

### 4. Prometheus 指标未采集

- 检查 `/metrics` 端点是否可访问
- 检查 Prometheus 配置中的端口是否正确
- 检查防火墙规则

## 开发计划

- [ ] 添加用户认证
- [ ] 支持更多导出格式（PDF、HTML）
- [ ] 添加文件管理功能
- [ ] 支持批量转换
- [ ] 添加转换历史记录
- [X] 添加 Prometheus 监控支持
- [X] 支持 Docker 多阶段构建
- [X] 支持 K8s 部署
