import os
import time

try:
    from app import app, init_db
    
    if __name__ == '__main__':
        try:
            # إذا كنا على Render، انتظر قليلاً للتأكد من جاهزية التطبيق
            if 'RENDER' in os.environ:
                time.sleep(2)
                
            with app.app_context():
                print("بدء استعادة بيانات المقررات والطلاب والدرجات...")
                init_db()
                print("تم استعادة البيانات بنجاح!")
        except Exception as e:
            print(f"حدث خطأ أثناء استعادة البيانات: {str(e)}")
            if 'RENDER' in os.environ:
                # في بيئة الإنتاج، نخرج بنجاح حتى لا يفشل النشر
                print("تجاهل الخطأ والاستمرار في النشر")
                exit(0)
            else:
                # في بيئة التطوير، نخرج برمز خطأ
                exit(1)
except ImportError as e:
    print(f"حدث خطأ أثناء استيراد app: {str(e)}")
    print("تجاهل هذا الخطأ والاستمرار في النشر")
    # نخرج بنجاح حتى لا يفشل النشر
    exit(0)
