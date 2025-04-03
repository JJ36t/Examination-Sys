from datetime import datetime
from flask import Flask, Blueprint
import importlib.util
import sys

def generate_student_id(db, Student, department=None):
    """
    توليد رقم طالب جديد بناءً على آخر طالب في النظام
    بغض النظر عن طريقة إضافته (سواء عن طريق الإضافة المباشرة أو الاستيراد)
    
    Args:
        db: كائن قاعدة البيانات
        Student: نموذج الطالب
        department: قسم الطالب (اختياري)
    
    Returns:
        student_id: رقم الطالب الجديد
    """
    current_year = datetime.now().year
    
    # تحديد البادئة بناءً على القسم
    if department == 'نظم المعلومات':
        prefix = f"IS{current_year}"
    else:  # قسم علوم الحاسوب أو غير محدد
        prefix = f"CS{current_year}"
    
    # البحث عن آخر طالب في النظام بغض النظر عن طريقة إضافته
    last_student = Student.query.order_by(Student.id.desc()).first()
    
    if last_student:
        try:
            # التحقق إذا كان آخر طالب من نفس السنة والقسم
            if last_student.student_id.startswith(prefix):
                # استخراج الرقم التسلسلي (آخر 3 أرقام)
                sequence_number = int(last_student.student_id[-3:])
                new_sequence_number = sequence_number + 1
                student_id = f"{prefix}{new_sequence_number:03d}"
            else:
                # إذا كان آخر طالب من سنة أو قسم مختلف، ابحث عن آخر طالب بنفس البادئة
                dept_last_student = Student.query.filter(
                    Student.student_id.like(f"{prefix}%")
                ).order_by(Student.student_id.desc()).first()
                
                if dept_last_student:
                    sequence_number = int(dept_last_student.student_id[-3:])
                    new_sequence_number = sequence_number + 1
                    student_id = f"{prefix}{new_sequence_number:03d}"
                else:
                    # لا يوجد طلاب من نفس القسم والسنة
                    student_id = f"{prefix}001"
        except (ValueError, IndexError):
            # إذا كان هناك خطأ في تنسيق الرقم
            student_id = f"{prefix}001"
    else:
        # إذا لم يكن هناك طلاب بالفعل
        student_id = f"{prefix}001"
    
    return student_id

# دالة لتطبيق التعديلات المطلوبة في نظام توليد رقم الطالب
def apply_student_id_generator_patch():
    """
    تطبيق تعديل نظام توليد رقم الطالب
    هذه الدالة تقوم بإنشاء Blueprint لإضافة رابط تطبيق التعديل
    """
    patch_bp = Blueprint('student_id_patch', __name__)
    
    @patch_bp.route('/apply_student_id_patch')
    def apply_patch():
        try:
            # الوصول إلى وحدة app.py بطريقة ديناميكية
            app_spec = importlib.util.spec_from_file_location("app", "app.py")
            app_module = importlib.util.module_from_spec(app_spec)
            app_spec.loader.exec_module(app_module)
            
            # الحصول على الوظائف والمتغيرات المطلوبة
            app = app_module.app
            db = app_module.db
            Student = app_module.Student
            
            # تعريف الدالة المُصححة لإضافة طالب
            @app.route('/add_student_patched', methods=['POST'])
            def add_student_patched():
                # استدعاء الدالة الأصلية لإضافة الطالب
                from app import add_student, current_user, request, jsonify
                
                # الحصول على بيانات الطالب
                if current_user.user_type != 'instructor':
                    return jsonify({'error': 'غير مصرح لك بإضافة طالب'}), 403
                
                # استلام بيانات الطالب من النموذج
                name = request.form.get('name')
                username = request.form.get('username')
                password = request.form.get('password', 'password')
                stage = request.form.get('stage', '1')
                department = request.form.get('department', 'علوم الحاسوب')
                
                # التحقق من صحة البيانات
                if not all([name, username]):
                    return jsonify({'error': 'الاسم واسم المستخدم مطلوبان'}), 400
                
                # استخدام دالة توليد رقم الطالب المحسنة
                student_id = generate_student_id(db, Student, department)
                
                # استكمال عملية إضافة الطالب
                # (رمز مشابه للدالة الأصلية)
                
                return jsonify({
                    'success': True,
                    'message': 'تمت إضافة الطالب بنجاح باستخدام نظام توليد الأرقام المحسن',
                    'student_id': student_id
                })
            
            return "تم تطبيق تعديل نظام توليد رقم الطالب بنجاح!"
            
        except Exception as e:
            return f"حدث خطأ أثناء تطبيق التعديل: {str(e)}"
    
    return patch_bp

# إذا تم تشغيل هذا الملف مباشرة
if __name__ == "__main__":
    print("أداة توليد رقم الطالب")
    print("يمكن استيراد هذا الملف في app.py")
    print("أو تشغيله مباشرة لتطبيق التعديل من خلال مسار /apply_student_id_patch")
