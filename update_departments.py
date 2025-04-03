from app import app, db, Student, User

def update_student_departments():
    with app.app_context():
        try:
            # الحصول على جميع الطلاب
            students = Student.query.all()
            
            # عرض الأقسام الحالية
            print("=== الأقسام الحالية ===")
            for student in students:
                user = User.query.get(student.user_id)
                print(f"الطالب: {user.name}, الرقم: {student.student_id}, القسم: {student.department}")
            
            print("\n=== تحديث الأقسام ===")
            
            # يمكنك تغيير هذه القيم حسب حاجتك
            departments = {
                "نظم المعلومات": ["ياسمين عادل", "حسن كريم"],  # أسماء الطلاب في قسم نظم المعلومات
                "علوم الحاسوب": []  # سيتم تعيين جميع الطلاب الآخرين إلى علوم الحاسوب
            }
            
            # تحديث الأقسام
            updated_count = 0
            for student in students:
                user = User.query.get(student.user_id)
                original_dept = student.department
                
                # البحث عن القسم المناسب
                assigned_dept = "علوم الحاسوب"  # القيمة الافتراضية
                for dept, names in departments.items():
                    if user.name in names:
                        assigned_dept = dept
                        break
                
                # تحديث القسم إذا لزم الأمر
                if original_dept != assigned_dept:
                    student.department = assigned_dept
                    updated_count += 1
                    print(f"تم تحديث الطالب: {user.name} من {original_dept} إلى {assigned_dept}")
            
            # حفظ التغييرات
            if updated_count > 0:
                db.session.commit()
                print(f"\nتم تحديث {updated_count} طالب بنجاح")
            else:
                print("\nلم يتم إجراء أي تغييرات")
            
            # عرض الأقسام بعد التحديث
            print("\n=== الأقسام بعد التحديث ===")
            for student in students:
                user = User.query.get(student.user_id)
                print(f"الطالب: {user.name}, الرقم: {student.student_id}, القسم: {student.department}")
            
        except Exception as e:
            db.session.rollback()
            print(f"حدث خطأ: {str(e)}")

if __name__ == "__main__":
    update_student_departments()
