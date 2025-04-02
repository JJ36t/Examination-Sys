"""
ملف نقطة دخول لتطبيق Flask على منصة Render.
استخدم هذا الملف كملف منفصل يقوم باستيراد وتشغيل التطبيق الرئيسي.
"""

import os
from app import app

if __name__ == '__main__':
    # تحقق مما إذا كنا على Render
    if 'RENDER' in os.environ:
        # تشغيل التطبيق على Render بدون تكوين SSL (Render يتعامل مع SSL)
        port = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # توليد شهادة SSL للبيئة المحلية فقط
        ssl_context = 'adhoc'
        app.run(debug=True, ssl_context=ssl_context, host='0.0.0.0')
