import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 1  # عامل واحد فقط لتجنب المشاكل
timeout = 240  # زيادة المهلة إلى 4 دقائق
worker_class = 'sync'
max_requests = 500
max_requests_jitter = 50
preload_app = False  # تعطيل التحميل المسبق لتجنب المشاكل
accesslog = '-'
errorlog = '-'
loglevel = 'debug'  # سجل التنقيح المفصل
reload = False  # لا تقم بإعادة التحميل التلقائي

# تمكين الوصول للمتغيرات البيئية في التطبيق
raw_env = [
    "RENDER=true",
]
