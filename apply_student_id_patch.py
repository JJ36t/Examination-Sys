from flask import Flask
from student_id_generator import generate_student_id, apply_student_id_generator_patch

# استيراد تطبيق Flask والنماذج من app.py
from app import app, db, Student

# تسجيل البلوبرنت لتطبيق التعديل
app.register_blueprint(apply_student_id_generator_patch())

# تعديل دالة توليد رقم الطالب الحالية
def patch_add_student_function():
    """
    تطبيق تعديل على وظيفة إضافة طالب لاستخدام دالة توليد رقم الطالب المحسنة
    """
    # طباعة رسالة لتأكيد تطبيق التعديل
    print("جاري تطبيق تعديل وظيفة توليد رقم الطالب...")
    
    # طباعة مثال على رقم طالب جديد
    example_id = generate_student_id(db, Student, 'علوم الحاسوب')
    print(f"مثال على رقم طالب جديد: {example_id}")
    
    return "تم تطبيق التعديل بنجاح!"

if __name__ == '__main__':
    patch_add_student_function()
    
    # تشغيل التطبيق بعد تطبيق التعديلات
    app.run(debug=True, host='127.0.0.1', port=5001)
