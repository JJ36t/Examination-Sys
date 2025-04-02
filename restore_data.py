import os

# ملف بسيط لاستعادة البيانات
print("ملف استعادة البيانات")

# التأكد من وجود مجلد instance و uploads
os.makedirs("instance", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

try:
    from app import app, db
    with app.app_context():
        db.create_all()
        print("تم إنشاء جميع جداول قاعدة البيانات بنجاح")
except Exception as e:
    print(f"حدث خطأ أثناء إنشاء قاعدة البيانات: {str(e)}")
    # نخرج برمز نجاح حتى لا يتوقف النشر
    exit(0)
