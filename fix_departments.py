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
            
            # تحديث بعض الطلاب لقسم نظم المعلومات
            # قائمة الطلاب المراد تحديثهم إلى قسم نظم المعلومات
            # يمكنك تعديل هذه القائمة حسب احتياجك
            info_systems_students = [
                "ياسمين عادل",
                "حسن كريم",
                "نور محمود",
                "زينب عبد الله"
            ]
            
            # تحديث الأقسام
            updated_count = 0
            for student in students:
                user = User.query.get(student.user_id)
                original_dept = student.department
                
                # تحديد القسم بناءً على اسم الطالب
                if user.name in info_systems_students:
                    assigned_dept = "نظم المعلومات"
                else:
                    assigned_dept = "علوم الحاسوب"
                
                # تحديث القسم
                student.department = assigned_dept
                updated_count += 1
                print(f"تحديث: {user.name} -> {assigned_dept}")
            
            # حفظ التغييرات في قاعدة البيانات
            db.session.commit()
            print(f"\nتم تحديث {updated_count} طالب بنجاح")
            
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
