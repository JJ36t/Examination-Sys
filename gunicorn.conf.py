import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 1
timeout = 120  # زيادة مهلة الانتظار
worker_class = 'sync'
max_requests = 1000
max_requests_jitter = 50
preload_app = True
accesslog = '-'
errorlog = '-'

# تمكين الوصول للمتغيرات البيئية في التطبيق
raw_env = [
    f"RENDER=true",
]
