"""
ملف نقطة دخول لتطبيق Flask على منصة Render.
هذا الملف يعمل كوسيط بين Gunicorn والتطبيق الرئيسي.
يستخدم في بيئة الإنتاج على منصة Render.
"""

import os
import sys

# إضافة المجلد الحالي إلى مسار النظام لضمان إمكانية استيراد الوحدات
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# للتعامل مع مشاكل الذاكرة على Render
nimport = 1024 * 1024 * 100  # 100MB

# استيراد كائن التطبيق من الملف الرئيسي
try:
    from app import app
    
    # التحقق من أن التطبيق تم استيراده بنجاح
    if not app:
        raise ImportError("Could not import Flask app instance from app.py")
        
    # إعداد متغيرات للتشغيل في بيئة الإنتاج
    if 'RENDER' in os.environ:
        print("Running in production mode on Render", file=sys.stderr)
        app.config['ENV'] = 'production'
        app.config['DEBUG'] = False

except Exception as e:
    # لا يمكن إخفاء الأخطاء عند بدء التشغيل
    print(f"ERROR INITIALIZING APPLICATION: {str(e)}", file=sys.stderr)
    raise

# للتشغيل المباشر (غير مستخدم مع Gunicorn)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
