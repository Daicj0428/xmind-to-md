"""
Prometheus monitoring module - export metrics for Prometheus scraping
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
from flask import Response, request
import time
import flask
from pathlib import Path


# ============ Metric Definitions ============

REQUEST_COUNT = Counter(
    'xmind_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'xmind_request_duration_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

UPLOAD_COUNT = Counter(
    'xmind_uploads_total',
    'Total file uploads',
    ['status']
)

UPLOAD_SIZE = Histogram(
    'xmind_upload_size_bytes',
    'Upload file size in bytes'
)

CONVERT_COUNT = Counter(
    'xmind_conversions_total',
    'Total conversions',
    ['format', 'status']
)

CONVERT_DURATION = Histogram(
    'xmind_conversion_duration_seconds',
    'Conversion duration in seconds',
    ['format']
)

TEMP_FILES_GAUGE = Gauge(
    'xmind_temp_files',
    'Number of temp files'
)

OUTPUT_FILES_GAUGE = Gauge(
    'xmind_output_files',
    'Number of output files'
)

DISK_USAGE_GAUGE = Gauge(
    'xmind_disk_usage_bytes',
    'Disk usage in bytes',
    ['type']
)


# ============ Helper Functions ============

def _get_dir_stats(path):
    """Get file count and total size for a directory"""
    count = 0
    size = 0
    p = Path(path)
    if p.exists():
        for f in p.rglob('*'):
            if f.is_file():
                count += 1
                try:
                    size += f.stat().st_size
                except:
                    pass
    return count, size


def update_file_gauges():
    """Auto-update gauges from disk"""
    temp_dir = Path('temp').resolve()
    output_dir = Path('output').resolve()
    temp_count, temp_bytes = _get_dir_stats(temp_dir)
    output_count, output_bytes = _get_dir_stats(output_dir)
    TEMP_FILES_GAUGE.set(temp_count)
    OUTPUT_FILES_GAUGE.set(output_count)
    DISK_USAGE_GAUGE.labels(type='temp').set(temp_bytes)
    DISK_USAGE_GAUGE.labels(type='output').set(output_bytes)


def track_upload(size_bytes):
    """Record upload metrics"""
    UPLOAD_COUNT.labels(status='success').inc()
    UPLOAD_SIZE.observe(size_bytes)


def track_upload_failure():
    """Record failed upload"""
    UPLOAD_COUNT.labels(status='failed').inc()


def track_conversion(fmt, duration, success=True):
    """Record conversion metrics"""
    status = 'success' if success else 'failed'
    CONVERT_COUNT.labels(format=fmt, status=status).inc()
    if success:
        CONVERT_DURATION.labels(format=fmt).observe(duration)


# ============ Flask Integration ============

def setup_metrics(app):
    """Setup Prometheus /metrics endpoint for Flask app"""

    @app.route('/metrics')
    def metrics():
        """Prometheus metrics endpoint"""
        update_file_gauges()
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    # Track all requests via before/after hooks
    @app.before_request
    def before_request():
        flask.g.start_time = time.time()

    @app.after_request
    def after_request(response):
        if hasattr(flask.g, 'start_time'):
            duration = time.time() - flask.g.start_time
            method = request.method
            endpoint = request.path
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=str(response.status_code)
            ).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
        return response

    return app
