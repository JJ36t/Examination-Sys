from app import app, db, User, Student, Course, Grade
import os, random
from datetime import datetime

def restore_all_data():
    with app.app_context():
        # تحقق من وجود قاعدة البيانات
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'examination.db')
        if not os.path.exists(os.path.dirname(db_path)):
            os.makedirs(os.path.dirname(db_path))
        
        db.create_all()  # إنشاء الجداول إن لم تكن موجودة
        
        # عرض حالة قاعدة البيانات الحالية
        print("=== حالة قاعدة البيانات الحالية ===")
        print(f"عدد المستخدمين: {User.query.count()}")
        print(f"عدد الطلاب: {Student.query.count()}")
        print(f"عدد المقررات: {Course.query.count()}")
        print(f"عدد الدرجات: {Grade.query.count()}")
        print("=" * 40)
        
        # مسح القاعدة وإعادة تعبئتها إذا كانت البيانات ناقصة أو إذا تم طلب إعادة التعبئة
        should_recreate = False
        
        # التحقق من وجود بيانات في الجداول
        if User.query.count() == 0 or Student.query.count() == 0 or Course.query.count() == 0 or Grade.query.count() == 0:
            should_recreate = True
            print("تم اكتشاف بيانات ناقصة... سيتم إعادة تعبئة قاعدة البيانات.")
        
        if should_recreate:
            # إعادة تعبئة قاعدة البيانات من البداية
            print("جاري إعادة تعبئة قاعدة البيانات...")
            
            # حذف البيانات الموجودة (إن وجدت)
            db.drop_all()
            db.create_all()
            
            # إضافة المستخدم المدرس
            instructor = User(
                username='instructor',
                name='د. محمد أحمد',
                user_type='instructor'
            )
            instructor.set_password('password')
            db.session.add(instructor)
            
            # إضافة المقررات الدراسية
            courses_data = [
                # المرحلة الأولى، الفصل الأول
                {'name': 'اساسيات برمجة', 'stage': 1, 'semester': 1, 'units': 8},
                {'name': 'مقدمة في تكنلوجيا المعلومات', 'stage': 1, 'semester': 1, 'units': 8},
                {'name': 'تصميم منطقي', 'stage': 1, 'semester': 1, 'units': 6},
                {'name': 'اقتصاد', 'stage': 1, 'semester': 1, 'units': 4},
                
                # المرحلة الأولى، الفصل الثاني
                {'name': 'هياكل متقطعة', 'stage': 1, 'semester': 2, 'units': 6},
                {'name': 'تركيب الحاسوب', 'stage': 1, 'semester': 2, 'units': 6},
                {'name': 'حقوق الانسان', 'stage': 1, 'semester': 2, 'units': 2},
                {'name': 'ديمقراطية', 'stage': 1, 'semester': 2, 'units': 2},
                
                # المرحلة الثانية، الفصل الأول
                {'name': 'برمجة كيانية', 'stage': 2, 'semester': 1, 'units': 8},
                {'name': 'طرق عددية', 'stage': 2, 'semester': 1, 'units': 6},
                {'name': 'معالجات دقيقة', 'stage': 2, 'semester': 1, 'units': 8},
                {'name': 'اللغة العربية', 'stage': 2, 'semester': 1, 'units': 2},
                
                # المرحلة الثانية، الفصل الثاني
                {'name': 'نظرية احتسابية', 'stage': 2, 'semester': 2, 'units': 4},
                {'name': 'هياكل بيانات', 'stage': 2, 'semester': 2, 'units': 8},
                {'name': 'احصاء', 'stage': 2, 'semester': 2, 'units': 4},
                {'name': 'جافا', 'stage': 2, 'semester': 2, 'units': 6},
                
                # المرحلة الثالثة، الفصل الأول
                {'name': 'بحث ويب', 'stage': 3, 'semester': 1, 'units': 4},
                {'name': 'برمجة مواقع', 'stage': 3, 'semester': 1, 'units': 6},
                {'name': 'رسم بالحاسوب', 'stage': 3, 'semester': 1, 'units': 8},
                {'name': 'قواعد بيانات', 'stage': 3, 'semester': 1, 'units': 8},
                
                # المرحلة الثالثة، الفصل الثاني
                {'name': 'مترجمات', 'stage': 3, 'semester': 2, 'units': 6},
                {'name': 'بايثون', 'stage': 3, 'semester': 2, 'units': 6},
                {'name': 'ذكاء اصطناعي', 'stage': 3, 'semester': 2, 'units': 6},
                {'name': 'تشفير', 'stage': 3, 'semester': 2, 'units': 4},
                
                # المرحلة الرابعة، الفصل الأول
                {'name': 'انترنيت الاشياء', 'stage': 4, 'semester': 1, 'units': 6},
                {'name': 'نظم تشغيل', 'stage': 4, 'semester': 1, 'units': 8},
                {'name': 'معالجة صور', 'stage': 4, 'semester': 1, 'units': 8},
                {'name': 'امنية حواسيب', 'stage': 4, 'semester': 1, 'units': 4},
                
                # المرحلة الرابعة، الفصل الثاني
                {'name': 'حوسبة سحابية', 'stage': 4, 'semester': 2, 'units': 4},
                {'name': 'تمييز انماط', 'stage': 4, 'semester': 2, 'units': 4},
                {'name': 'شبكات', 'stage': 4, 'semester': 2, 'units': 8},
                {'name': 'تجارة الكترونية', 'stage': 4, 'semester': 2, 'units': 4},
            ]
            
            for course_data in courses_data:
                course = Course(**course_data)
                db.session.add(course)
            
            # إضافة الطلاب
            students_data = [
                {'name': 'أحمد علي', 'username': 'ahmed', 'student_id': 'CS2023001', 'stage': 1},
                {'name': 'فاطمة محمد', 'username': 'fatima', 'student_id': 'CS2023002', 'stage': 1},
                {'name': 'علي حسين', 'username': 'ali', 'student_id': 'CS2023003', 'stage': 1},
                {'name': 'زينب عبد الله', 'username': 'zainab', 'student_id': 'CS2022001', 'stage': 2},
                {'name': 'حسن كريم', 'username': 'hassan', 'student_id': 'CS2022002', 'stage': 2},
                {'name': 'نور محمود', 'username': 'noor', 'student_id': 'CS2021001', 'stage': 3},
                {'name': 'محمد جاسم', 'username': 'mohammed', 'student_id': 'CS2021002', 'stage': 3},
                {'name': 'سارة أحمد', 'username': 'sara', 'student_id': 'CS2020001', 'stage': 4},
                {'name': 'عمر فاضل', 'username': 'omar', 'student_id': 'CS2020002', 'stage': 4},
                {'name': 'مصطفى كاظم', 'username': 'mustafa', 'student_id': 'CS2023004', 'stage': 1},
                {'name': 'ياسمين عادل', 'username': 'yasmin', 'student_id': 'CS2022003', 'stage': 2},
                {'name': 'حسين علي', 'username': 'hussein', 'student_id': 'CS2021003', 'stage': 3},
                {'name': 'رنا محمد', 'username': 'rana', 'student_id': 'CS2020003', 'stage': 4},
                {'name': 'يوسف أحمد', 'username': 'yousef', 'student_id': 'CS2023005', 'stage': 1},
                {'name': 'زيد عبد الكريم', 'username': 'zaid', 'student_id': 'CS2023006', 'stage': 1},
                {'name': 'سجى محمود', 'username': 'saja', 'student_id': 'CS2022004', 'stage': 2},
                {'name': 'عبد الله جاسم', 'username': 'abdullah', 'student_id': 'CS2021004', 'stage': 3},
                {'name': 'ليلى حسن', 'username': 'layla', 'student_id': 'CS2020004', 'stage': 4},
                {'name': 'مريم علي', 'username': 'mariam', 'student_id': 'CS2023007', 'stage': 1},
            ]
            
            for student_data in students_data:
                user = User(
                    username=student_data['username'],
                    name=student_data['name'],
                    user_type='student'
                )
                user.set_password('password')
                db.session.add(user)
                db.session.flush()  # للحصول على معرف المستخدم
                
                student = Student(
                    user_id=user.id,
                    student_id=student_data['student_id'],
                    stage=student_data['stage']
                )
                db.session.add(student)
            
            db.session.commit()
            
            # إضافة الدرجات
            students = Student.query.all()
            courses = Course.query.all()
            
            for student in students:
                for course in courses:
                    if course.stage == student.stage:
                        # إضافة درجات فقط لمقررات المرحلة الحالية للطالب
                        grade = Grade(
                            student_id=student.id,
                            course_id=course.id,
                            coursework=random.randint(30, 45),
                            final_exam=random.randint(30, 45),
                            decision_marks=random.randint(0, 5),
                            academic_year=f"{datetime.now().year-1}/{datetime.now().year}"
                        )
                        db.session.add(grade)
            
            db.session.commit()
            
            print("تم إعادة تعبئة قاعدة البيانات بنجاح!")
        else:
            print("لا حاجة لإعادة تعبئة قاعدة البيانات. جميع البيانات موجودة بالفعل.")
        
        # عرض حالة قاعدة البيانات بعد الإعادة
        print("\n=== حالة قاعدة البيانات النهائية ===")
        print(f"عدد المستخدمين: {User.query.count()}")
        print(f"عدد الطلاب: {Student.query.count()}")
        print(f"عدد المقررات: {Course.query.count()}")
        print(f"عدد الدرجات: {Grade.query.count()}")
        print("=" * 40)
        
        # عرض معلومات تسجيل الدخول
        print("\n=== معلومات تسجيل الدخول ===")
        print("المدرس:")
        print("  اسم المستخدم: instructor")
        print("  كلمة المرور: password")
        print("\nالطلاب:")
        print("  اسم المستخدم: (مثل: ahmed, fatima, ali, ...)")
        print("  كلمة المرور: password (لجميع الطلاب)")
        print("=" * 40)

if __name__ == "__main__":
    restore_all_data()
