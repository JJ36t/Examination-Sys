import re
import sys
import os

def patch_app_file():
    """تطبيق تعديلات توليد رقم الطالب على ملف app.py"""
    
    app_file_path = "app.py"
    backup_file_path = "app_py_backup.py"
    
    try:
        # إنشاء نسخة احتياطية من الملف الأصلي
        if not os.path.exists(backup_file_path):
            with open(app_file_path, 'r', encoding='utf-8') as src:
                with open(backup_file_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            print(f"تم إنشاء نسخة احتياطية: {backup_file_path}")
        
        # قراءة محتوى الملف
        with open(app_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 1. إضافة استيراد دالة توليد رقم الطالب
        import_pattern = r'from OpenSSL import crypto'
        import_replacement = 'from OpenSSL import crypto\n# استيراد دالة توليد رقم الطالب\nfrom student_id_generator import generate_student_id'
        content = content.replace(import_pattern, import_replacement)
        
        # 2. تعديل دالة add_student
        # البحث عن جزء توليد رقم الطالب في دالة add_student
        add_student_pattern = r'# البحث عن آخر طالب بنفس السنة والقسم\s+last_student = Student\.query\.filter\((.*?)\s+\# التحقق من عدم وجود رقم طالب مكرر'
        
        # النص البديل لتوليد رقم الطالب
        add_student_replacement = """# استخدام دالة توليد رقم الطالب المحسنة
    student_id = generate_student_id(db, Student, department)
    
    # التحقق من عدم وجود رقم طالب مكرر"""
        
        # تطبيق التعديل باستخدام التعبيرات العادية
        content = re.sub(add_student_pattern, add_student_replacement, content, flags=re.DOTALL)
        
        # 3. تعديل دالة generate_student_id في import_students
        import_generate_id_pattern = r'def generate_student_id\(\):(.*?)return student_id'
        
        # النص البديل لدالة توليد رقم الطالب في استيراد الطلاب
        import_generate_id_replacement = """def generate_student_id():
        # استخدام دالة توليد رقم الطالب المحسنة
        return generate_student_id(db, Student)"""
        
        # تطبيق التعديل
        content = re.sub(import_generate_id_pattern, import_generate_id_replacement, content, flags=re.DOTALL)
        
        # 4. حفظ التغييرات في الملف
        with open(app_file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        
        print("تم تطبيق التعديلات بنجاح على ملف app.py!")
        return True
        
    except Exception as e:
        print(f"حدث خطأ أثناء تطبيق التعديلات: {str(e)}")
        return False

if __name__ == "__main__":
    if patch_app_file():
        print("تم تطبيق تعديلات توليد رقم الطالب بنجاح!")
    else:
        print("فشل تطبيق التعديلات، يرجى التحقق من الأخطاء أعلاه.")
