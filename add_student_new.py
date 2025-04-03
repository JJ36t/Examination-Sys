@app.route('/add_student', methods=['POST'])
@login_required
def add_student():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'غير مصرح لك بإضافة طالب'}), 403
    
    # استلام بيانات الطالب من النموذج
    name = request.form.get('name')
    username = request.form.get('username')
    password = request.form.get('password', 'password')  # كلمة مرور افتراضية إذا لم يتم تحديدها
    stage = request.form.get('stage', '1')  # استلام المرحلة من النموذج، ووضع المرحلة الأولى كقيمة افتراضية
    department = request.form.get('department', 'علوم الحاسوب')  # استلام القسم من النموذج
    
    # التحقق من صحة البيانات
    if not all([name, username]):
        return jsonify({'error': 'الاسم واسم المستخدم مطلوبان'}), 400
    
    # التحقق من صحة القسم
    if department not in ['علوم الحاسوب', 'نظم المعلومات']:
        return jsonify({'error': 'القسم يجب أن يكون إما علوم الحاسوب أو نظم المعلومات'}), 400
    
    # التحقق من عدم وجود اسم مستخدم مكرر
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'اسم المستخدم موجود بالفعل'}), 400
    
    current_year = datetime.now().year
    
    # تعيين بادئة الرقم بناءً على القسم
    if department == 'علوم الحاسوب':
        year_prefix = f"CS{current_year}"
    else:  # قسم نظم المعلومات
        year_prefix = f"IS{current_year}"
    
    # البحث عن آخر طالب في قاعدة البيانات بغض النظر عن طريقة الإضافة
    latest_student = Student.query.order_by(Student.id.desc()).first()
    
    # متغير لتخزين رقم الطالب الجديد
    new_sequence_number = 1  # قيمة افتراضية
    
    if latest_student and latest_student.student_id:
        try:
            # محاولة استخراج الرقم التسلسلي (آخر 3 أرقام)
            sequence_number = int(latest_student.student_id[-3:])
            new_sequence_number = sequence_number + 1
        except (ValueError, IndexError):
            # إذا كان هناك خطأ في تنسيق الرقم، استخدم الرقم 1
            new_sequence_number = 1
    
    # توليد رقم الطالب بناءً على البادئة والرقم التسلسلي
    student_id = f"{year_prefix}{new_sequence_number:03d}"
    
    # التأكد من أن الرقم غير مكرر
    while Student.query.filter_by(student_id=student_id).first():
        new_sequence_number += 1
        student_id = f"{year_prefix}{new_sequence_number:03d}"
    
    try:
        # إنشاء حساب المستخدم
        user = User(
            username=username,
            name=name,
            user_type='student'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # للحصول على معرف المستخدم
        
        # إنشاء طالب جديد
        student = Student(
            user_id=user.id,
            student_id=student_id,
            stage=int(stage),  # استخدام المرحلة المحددة من النموذج
            department=department  # استخدام القسم المحدد من النموذج
        )
        db.session.add(student)
        success_count = 1
        
        # إنشاء سجلات درجات فارغة للطالب
        courses = Course.query.filter_by(stage=int(stage)).all()  # استخدام المرحلة المحددة
        for course in courses:
            grade = Grade(
                student_id=student.id,
                course_id=course.id,
                coursework=0,
                final_exam=0,
                decision_marks=0,
                academic_year=f"{datetime.now().year-1}/{datetime.now().year+1}"
            )
            db.session.add(grade)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تمت إضافة الطالب بنجاح',
            'student': {
                'id': student.id,
                'name': user.name,
                'username': user.username,
                'student_id': student.student_id,
                'stage': student.stage,
                'department': student.department
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء إضافة الطالب: {str(e)}'}), 500
