from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import sqlite3
import pandas as pd
import json
from werkzeug.utils import secure_filename

# تكوين مجلد لتخزين الملفات المرفوعة
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

# التأكد من وجود مجلد التحميل
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///examination.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQL_SCHEMA_FILE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database_schema.sql')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'instructor' or 'student'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    stage = db.Column(db.Integer, nullable=False)  # 1, 2, 3, or 4
    grades = db.relationship('Grade', backref='student', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stage = db.Column(db.Integer, nullable=False)  # 1, 2, 3, or 4
    semester = db.Column(db.Integer, nullable=False)  # 1 or 2
    units = db.Column(db.Integer, nullable=False)  # between 2-8
    grades = db.relationship('Grade', backref='course', lazy=True)

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    coursework = db.Column(db.Integer, nullable=False, default=0)  # 0-50
    final_exam = db.Column(db.Integer, nullable=False, default=0)  # 0-50
    decision_marks = db.Column(db.Integer, nullable=False, default=0)  # 0-10
    academic_year = db.Column(db.String(20), nullable=False)
    
    @property
    def total(self):
        return self.coursework + self.final_exam + self.decision_marks
    
    @property
    def grade_status(self):
        if self.total < 50:
            return "راسب"
        return "ناجح"
    
    @property
    def grade_evaluation(self):
        total = self.total
        if total < 50:
            return "ضعيف"
        elif total < 60:
            return "مقبول"
        elif total < 70:
            return "متوسط"
        elif total < 80:
            return "جيد"
        elif total < 90:
            return "جيد جدا"
        else:
            return "امتياز"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.user_type == user_type:
            login_user(user)
            if user.user_type == 'instructor':
                return redirect(url_for('instructor_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('خطأ في اسم المستخدم أو كلمة المرور أو نوع المستخدم', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/instructor/dashboard')
@login_required
def instructor_dashboard():
    if current_user.user_type != 'instructor':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    stages = [1, 2, 3, 4]
    return render_template('instructor_dashboard.html', stages=stages)

@app.route('/instructor/modifications')
@login_required
def student_modifications():
    if current_user.user_type != 'instructor':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    stages = [1, 2, 3, 4]
    return render_template('student_modifications.html', stages=stages)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.user_type != 'student':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash('لم يتم العثور على بيانات الطالب', 'danger')
        return redirect(url_for('login'))
    
    stages = [1, 2, 3, 4]
    semesters = [1, 2]
    
    all_grades = {}
    stage_gpas = {}  # لتخزين المعدل النهائي لكل مرحلة
    
    for stage in stages:
        all_grades[stage] = {}
        # حساب المعدل النهائي للمرحلة
        stage_gpas[stage] = calculate_stage_gpa(student.id, stage)
        
        for semester in semesters:
            courses = Course.query.filter_by(stage=stage, semester=semester).all()
            grades = []
            for course in courses:
                grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
                if grade:
                    grades.append({
                        'course': course,
                        'grade': grade
                    })
            all_grades[stage][semester] = grades
    
    return render_template('student_dashboard.html', all_grades=all_grades, stages=stages, semesters=semesters, stage_gpas=stage_gpas)

@app.route('/get_students_by_stage_semester', methods=['POST'])
@login_required
def get_students_by_stage_semester():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    stage = request.form.get('stage')
    semester = request.form.get('semester')
    
    if not stage or not semester:
        return jsonify({'error': 'Missing parameters'}), 400
    
    # تعديل: جلب جميع الطلاب بدلاً من تصفية حسب المرحلة
    students = Student.query.order_by(Student.student_id).all()
    courses = Course.query.filter_by(stage=stage, semester=semester).all()
    
    result = []
    for student in students:
        user = User.query.get(student.user_id)
        
        # حساب المعدل النهائي للكورس
        semester_gpa = calculate_semester_gpa(student.id, stage, semester)
        
        # حساب المعدل النهائي للمرحلة (فقط إذا كان الكورس الثاني)
        stage_gpa = None
        if semester == '2' or semester == 2:
            stage_gpa = calculate_stage_gpa(student.id, stage)
        
        student_data = {
            'id': student.id,
            'name': user.name,
            'student_id': student.student_id,
            'grades': [],
            'semester_gpa': round(semester_gpa, 4),
            'stage_gpa': round(stage_gpa, 4) if stage_gpa is not None else None
        }
        
        for course in courses:
            grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
            if not grade:
                # Create empty grade if not exists
                grade = Grade(
                    student_id=student.id,
                    course_id=course.id,
                    coursework=0,
                    final_exam=0,
                    decision_marks=0,
                    academic_year=f"{datetime.now().year-1}/{datetime.now().year}"
                )
                db.session.add(grade)
                db.session.commit()
            
            student_data['grades'].append({
                'grade_id': grade.id,
                'course_id': course.id,
                'course_name': course.name,
                'coursework': grade.coursework,
                'final_exam': grade.final_exam,
                'decision_marks': grade.decision_marks,
                'units': course.units,
                'total': grade.total,
                'evaluation': grade.grade_evaluation
            })
        
        result.append(student_data)
    
    return jsonify(result)

@app.route('/search_student', methods=['POST'])
@login_required
def search_student():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    search_term = request.form.get('search_term')
    stage = request.form.get('stage')
    semester = request.form.get('semester')
    
    if not search_term or not stage or not semester:
        return jsonify({'error': 'Missing parameters'}), 400
    
    # استعلام للطلاب الذين يبدأ اسمهم بكلمة البحث (أولوية أولى)
    students_starting_with = db.session.query(Student, User).join(User, Student.user_id == User.id).filter(
        (User.name.like(f'{search_term}%') | Student.student_id.like(f'{search_term}%'))
    ).order_by(Student.student_id).all()
    
    # استعلام للطلاب الذين يحتوي اسمهم على كلمة البحث في أي مكان آخر (أولوية ثانية)
    students_containing = db.session.query(Student, User).join(User, Student.user_id == User.id).filter(
        (User.name.like(f'%{search_term}%') & ~User.name.like(f'{search_term}%')) | 
        (Student.student_id.like(f'%{search_term}%') & ~Student.student_id.like(f'{search_term}%'))
    ).order_by(Student.student_id).all()
    
    # دمج النتائج مع الحفاظ على الأولوية
    all_students = students_starting_with + students_containing
    
    courses = Course.query.filter_by(stage=stage, semester=semester).all()
    
    result = []
    for student, user in all_students:
        student_data = {
            'id': student.id,
            'name': user.name,
            'student_id': student.student_id,
            'grades': []
        }
        
        for course in courses:
            grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
            if grade:
                student_data['grades'].append({
                    'grade_id': grade.id,
                    'course_id': course.id,
                    'course_name': course.name,
                    'coursework': grade.coursework,
                    'final_exam': grade.final_exam,
                    'decision_marks': grade.decision_marks,
                    'units': course.units,
                    'total': grade.total,
                    'evaluation': grade.grade_evaluation
                })
        
        result.append(student_data)
    
    return jsonify(result)

@app.route('/update_grade', methods=['POST'])
@login_required
def update_grade():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    grade_id = request.form.get('grade_id')
    coursework = request.form.get('coursework')
    final_exam = request.form.get('final_exam')
    decision_marks = request.form.get('decision_marks')
    
    if not grade_id or not coursework or not final_exam or not decision_marks:
        return jsonify({'error': 'Missing parameters'}), 400
    
    grade = Grade.query.get(grade_id)
    if not grade:
        return jsonify({'error': 'Grade not found'}), 404
    
    # Validate input values
    try:
        coursework_val = int(coursework)
        final_exam_val = int(final_exam)
        decision_marks_val = int(decision_marks)
        
        if not (0 <= coursework_val <= 50 and 0 <= final_exam_val <= 50 and 0 <= decision_marks_val <= 10):
            return jsonify({'error': 'Invalid grade values'}), 400
        
        grade.coursework = coursework_val
        grade.final_exam = final_exam_val
        grade.decision_marks = decision_marks_val
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'total': grade.total,
            'evaluation': grade.grade_evaluation
        })
    except ValueError:
        return jsonify({'error': 'Invalid input values'}), 400

@app.route('/instructor/reports')
@login_required
def instructor_reports():
    if current_user.user_type != 'instructor':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    return render_template('instructor_reports.html')

@app.route('/get_courses', methods=['POST'])
@login_required
def get_courses():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    stage = request.form.get('stage')
    semester = request.form.get('semester')
    
    if not stage or not semester:
        return jsonify({'error': 'Missing parameters'}), 400
    
    courses = Course.query.filter_by(stage=stage, semester=semester).all()
    
    result = []
    for course in courses:
        result.append({
            'id': course.id,
            'name': course.name,
            'units': course.units
        })
    
    return jsonify(result)

@app.route('/get_filtered_students', methods=['POST'])
@login_required
def get_filtered_students():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    stage = request.form.get('stage')
    semester = request.form.get('semester')
    course_id = request.form.get('course_id')
    report_type = request.form.get('report_type', 'all')
    
    if not stage or not semester:
        return jsonify({'error': 'Missing parameters'}), 400
    
    # تحويل المعلمات إلى أرقام
    stage = int(stage)
    semester = int(semester)
    
    students = Student.query.all()
    
    # جلب المواد الدراسية للمرحلة والكورس المحددين
    if course_id and course_id != 'all':
        courses = Course.query.filter_by(id=course_id).all()
    else:
        courses = Course.query.filter_by(stage=stage, semester=semester).all()
    
    result = []
    for student in students:
        user = User.query.get(student.user_id)
        
        # حساب المعدل النهائي للكورس
        semester_gpa = calculate_semester_gpa(student.id, stage, semester)
        
        # حساب المعدل النهائي للمرحلة (فقط إذا كان الكورس الثاني)
        stage_gpa = None
        if semester == 2:
            stage_gpa = calculate_stage_gpa(student.id, stage)
        
        # جلب درجات الطالب للمواد المحددة
        student_grades = []
        total_points = 0
        total_units = 0
        passed_courses = 0
        failed_courses = 0
        
        for course in courses:
            grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
            if grade:
                student_grades.append({
                    'grade_id': grade.id,
                    'course_id': course.id,
                    'course_name': course.name,
                    'coursework': grade.coursework,
                    'final_exam': grade.final_exam,
                    'decision_marks': grade.decision_marks,
                    'units': course.units,
                    'total': grade.total,
                    'evaluation': grade.grade_evaluation
                })
                
                # حساب المعدل المرجح بالوحدات
                total_points += grade.total * course.units
                total_units += course.units
                
                if grade.total >= 50:
                    passed_courses += 1
                else:
                    failed_courses += 1
        
        # إذا لم يكن للطالب درجات في هذه المرحلة والكورس والمادة، تخطي
        if not student_grades:
            continue
        
        # حساب المعدل
        average = total_points / total_units if total_units > 0 else 0
        
        # تحديد التقييم العام
        overall_evaluation = ''
        if average < 50:
            overall_evaluation = 'ضعيف'
        elif average < 60:
            overall_evaluation = 'مقبول'
        elif average < 70:
            overall_evaluation = 'متوسط'
        elif average < 80:
            overall_evaluation = 'جيد'
        elif average < 90:
            overall_evaluation = 'جيد جدا'
        else:
            overall_evaluation = 'امتياز'
        
        student_data = {
            'id': student.id,
            'name': user.name,
            'student_id': student.student_id,
            'stage': student.stage,
            'grades': student_grades,
            'average': average,
            'passed_courses': passed_courses,
            'failed_courses': failed_courses,
            'total_courses': len(student_grades),
            'evaluation': overall_evaluation,
            'semester_gpa': round(semester_gpa, 4),
            'stage_gpa': round(stage_gpa, 4) if stage_gpa is not None else None
        }
        
        result.append(student_data)
    
    # ترتيب الطلاب حسب الاسم (أبجدياً)
    result.sort(key=lambda x: x['name'])
    
    # تصفية النتائج حسب نوع التقرير
    if report_type == 'top10':
        # في حالة العشرة الأوائل، نقوم أولاً بالترتيب حسب المعدل ثم نأخذ أول 10 طلاب
        result.sort(key=lambda x: x['average'], reverse=True)
        result = result[:10]
    elif report_type == 'failed':
        result = [s for s in result if s['failed_courses'] > 0]  # الطلاب الراسبين
    elif report_type == 'passed':
        result = [s for s in result if s['failed_courses'] == 0]  # الطلاب الناجحين
    
    return jsonify(result)

@app.route('/get_all_students', methods=['POST'])
@login_required
def get_all_students():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    stage = request.form.get('stage')
    semester = request.form.get('semester')
    report_type = request.form.get('report_type', 'all')
    
    if not stage or not semester:
        return jsonify({'error': 'Missing parameters'}), 400
    
    # جلب جميع الطلاب
    students = Student.query.all()
    courses = Course.query.filter_by(stage=stage, semester=semester).all()
    
    result = []
    for student in students:
        user = User.query.get(student.user_id)
        
        # جلب درجات الطالب للمواد المحددة
        student_grades = []
        total_points = 0
        total_units = 0
        passed_courses = 0
        failed_courses = 0
        
        for course in courses:
            grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
            if grade:
                student_grades.append({
                    'grade_id': grade.id,
                    'course_id': course.id,
                    'course_name': course.name,
                    'coursework': grade.coursework,
                    'final_exam': grade.final_exam,
                    'decision_marks': grade.decision_marks,
                    'units': course.units,
                    'total': grade.total,
                    'evaluation': grade.grade_evaluation
                })
                
                # حساب المعدل المرجح بالوحدات
                total_points += grade.total * course.units
                total_units += course.units
                
                if grade.total >= 50:
                    passed_courses += 1
                else:
                    failed_courses += 1
        
        # إذا لم يكن للطالب درجات في هذه المرحلة والفصل، تخطي
        if not student_grades:
            continue
        
        # حساب المعدل
        average = total_points / total_units if total_units > 0 else 0
        
        # تحديد التقييم العام
        overall_evaluation = ''
        if average < 50:
            overall_evaluation = 'ضعيف'
        elif average < 60:
            overall_evaluation = 'مقبول'
        elif average < 70:
            overall_evaluation = 'متوسط'
        elif average < 80:
            overall_evaluation = 'جيد'
        elif average < 90:
            overall_evaluation = 'جيد جدا'
        else:
            overall_evaluation = 'امتياز'
        
        student_data = {
            'id': student.id,
            'name': user.name,
            'student_id': student.student_id,
            'stage': student.stage,
            'grades': student_grades,
            'average': average,
            'passed_courses': passed_courses,
            'failed_courses': failed_courses,
            'total_courses': len(student_grades),
            'evaluation': overall_evaluation,
            'semester_gpa': round(calculate_semester_gpa(student.id, stage, semester), 4),
            'stage_gpa': round(calculate_stage_gpa(student.id, stage), 4) if stage else None
        }
        
        result.append(student_data)
    
    # ترتيب الطلاب حسب الاسم (أبجدياً)
    result.sort(key=lambda x: x['name'])
    
    # تصفية النتائج حسب نوع التقرير
    if report_type == 'top10':
        # في حالة العشرة الأوائل، نقوم أولاً بالترتيب حسب المعدل ثم نأخذ أول 10 طلاب
        result.sort(key=lambda x: x['average'], reverse=True)
        result = result[:10]
    elif report_type == 'failed':
        result = [s for s in result if s['failed_courses'] > 0]  # الطلاب الراسبين
    elif report_type == 'passed':
        result = [s for s in result if s['failed_courses'] == 0]  # الطلاب الناجحين
    
    return jsonify(result)

@app.route('/add_student', methods=['POST'])
@login_required
def add_student():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'غير مصرح لك بإضافة طالب'}), 403
    
    # استلام بيانات الطالب من النموذج
    name = request.form.get('name')
    username = request.form.get('username')
    password = request.form.get('password', 'password')  # كلمة مرور افتراضية إذا لم يتم تحديدها
    
    # التحقق من صحة البيانات
    if not all([name, username]):
        return jsonify({'error': 'الاسم واسم المستخدم مطلوبان'}), 400
    
    # التحقق من عدم وجود اسم مستخدم مكرر
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'اسم المستخدم موجود بالفعل'}), 400
    
    current_year = datetime.now().year
    year_prefix = f"CS{current_year}"
    
    # البحث عن آخر طالب بنفس السنة
    last_student = Student.query.filter(Student.student_id.like(f"{year_prefix}%")).order_by(Student.student_id.desc()).first()
    
    if last_student:
        # استخراج الرقم التسلسلي من رقم الطالب وزيادته بواحد
        try:
            # استخراج الرقم التسلسلي (آخر 3 أرقام)
            sequence_number = int(last_student.student_id[-3:])
            new_sequence_number = sequence_number + 1
            student_id = f"{year_prefix}{new_sequence_number:03d}"
        except (ValueError, IndexError):
            # إذا كان هناك خطأ في تنسيق الرقم، ابدأ من 001
            student_id = f"{year_prefix}001"
    else:
        # إذا لم يكن هناك طلاب لهذه السنة، ابدأ من 001
        student_id = f"{year_prefix}001"
    
    # التحقق من عدم وجود رقم طالب مكرر
    if Student.query.filter_by(student_id=student_id).first():
        return jsonify({'error': 'رقم الطالب موجود بالفعل'}), 400
    
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
            stage=1  # تعيين المرحلة الأولى افتراضيًا
        )
        db.session.add(student)
        db.session.commit()
        
        # إنشاء سجلات درجات فارغة للطالب
        courses = Course.query.filter_by(stage=1).all()  # المرحلة الأولى افتراضيًا
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
                'stage': student.stage
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء إضافة الطالب: {str(e)}'}), 500

@app.route('/get_all_students_for_modification')
@login_required
def get_all_students_for_modification():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'غير مصرح لك بالوصول إلى هذه البيانات'}), 403
    
    students = Student.query.order_by(Student.stage, Student.student_id).all()
    result = []
    
    for student in students:
        user = User.query.get(student.user_id)
        result.append({
            'id': student.id,
            'user_id': student.user_id,
            'name': user.name,
            'username': user.username,
            'student_id': student.student_id,
            'stage': student.stage
        })
    
    return jsonify(result)

@app.route('/search_student_for_modification', methods=['POST'])
@login_required
def search_student_for_modification():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'غير مصرح لك بالوصول إلى هذه البيانات'}), 403
    
    search_term = request.form.get('search_term', '')
    if not search_term:
        return jsonify([])
    
    # البحث في اسم الطالب ورقم الطالب واسم المستخدم
    students = []
    
    # البحث في جدول المستخدمين (الاسم واسم المستخدم)
    users = User.query.filter(
        (User.user_type == 'student') & 
        ((User.name.like(f'%{search_term}%')) | 
         (User.username.like(f'%{search_term}%')))
    ).all()
    
    user_ids = [user.id for user in users]
    
    # البحث في جدول الطلاب (رقم الطالب)
    students_by_id = Student.query.filter(
        (Student.student_id.like(f'%{search_term}%')) | 
        (Student.user_id.in_(user_ids))
    ).all()
    
    for student in students_by_id:
        user = User.query.get(student.user_id)
        students.append({
            'id': student.id,
            'user_id': student.user_id,
            'name': user.name,
            'username': user.username,
            'student_id': student.student_id,
            'stage': student.stage
        })
    
    return jsonify(students)

@app.route('/update_student', methods=['POST'])
@login_required
def update_student():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'غير مصرح لك بتعديل بيانات الطالب'}), 403
    
    # استلام بيانات الطالب من النموذج
    student_id = request.form.get('student_id')
    user_id = request.form.get('user_id')
    name = request.form.get('name')
    username = request.form.get('username')
    student_id_number = request.form.get('student_id_number')
    stage = request.form.get('stage')
    password = request.form.get('password')
    
    # التحقق من صحة البيانات
    if not all([student_id, user_id, name, username, student_id_number, stage]):
        return jsonify({'error': 'جميع الحقول مطلوبة باستثناء كلمة المرور'}), 400
    
    try:
        # التحقق من عدم وجود اسم مستخدم مكرر
        existing_user = User.query.filter(User.username == username, User.id != int(user_id)).first()
        if existing_user:
            return jsonify({'error': 'اسم المستخدم موجود بالفعل'}), 400
        
        # التحقق من عدم وجود رقم طالب مكرر
        existing_student = Student.query.filter(Student.student_id == student_id_number, Student.id != int(student_id)).first()
        if existing_student:
            return jsonify({'error': 'رقم الطالب موجود بالفعل'}), 400
        
        # تحديث بيانات المستخدم
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'لم يتم العثور على المستخدم'}), 404
        
        user.name = name
        user.username = username
        
        # تحديث كلمة المرور إذا تم تقديمها
        if password:
            user.set_password(password)
        
        # تحديث بيانات الطالب
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'لم يتم العثور على الطالب'}), 404
        
        student.student_id = student_id_number
        student.stage = int(stage)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث بيانات الطالب بنجاح'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء تحديث بيانات الطالب: {str(e)}'}), 500

@app.route('/delete_student', methods=['POST'])
@login_required
def delete_student():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'غير مصرح لك بحذف الطالب'}), 403
    
    student_id = request.form.get('student_id')
    
    if not student_id:
        return jsonify({'error': 'معرف الطالب مطلوب'}), 400
    
    try:
        # البحث عن الطالب
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'لم يتم العثور على الطالب'}), 404
        
        # حذف درجات الطالب أولاً
        Grade.query.filter_by(student_id=student.id).delete()
        
        # حفظ معرف المستخدم قبل حذف الطالب
        user_id = student.user_id
        
        # حذف الطالب
        db.session.delete(student)
        
        # حذف المستخدم المرتبط بالطالب
        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم حذف الطالب بنجاح'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء حذف الطالب: {str(e)}'}), 500

# حساب المعدل النهائي للمرحلة (GPA)
def calculate_stage_gpa(student_id, stage):
    """
    حساب المعدل النهائي للمرحلة باستخدام المعادلة:
    GPA = ∑(درجة المادة × عدد وحدات المادة) / ∑(عدد وحدات المواد)
    """
    # جلب جميع المقررات للمرحلة المحددة
    courses = Course.query.filter_by(stage=stage).all()
    
    if not courses:
        return 0
    
    total_weighted_grades = 0
    total_units = 0
    
    for course in courses:
        # جلب درجة الطالب لهذا المقرر
        grade = Grade.query.filter_by(student_id=student_id, course_id=course.id).first()
        
        if grade:
            # حساب الدرجة المرجحة (درجة المادة × عدد وحدات المادة)
            weighted_grade = grade.total * course.units
            total_weighted_grades += weighted_grade
            total_units += course.units
    
    # حساب المعدل النهائي
    if total_units > 0:
        return total_weighted_grades / total_units
    else:
        return 0

# حساب المعدل النهائي للكورس (GPA)
def calculate_semester_gpa(student_id, stage, semester):
    """
    حساب المعدل النهائي للكورس باستخدام المعادلة:
    GPA = ∑(درجة المادة × عدد وحدات المادة) / ∑(عدد وحدات المواد)
    """
    # جلب جميع المقررات للمرحلة والكورس المحددين
    courses = Course.query.filter_by(stage=stage, semester=semester).all()
    
    if not courses:
        return 0
    
    total_weighted_grades = 0
    total_units = 0
    
    for course in courses:
        # جلب درجة الطالب لهذا المقرر
        grade = Grade.query.filter_by(student_id=student_id, course_id=course.id).first()
        
        if grade:
            # حساب الدرجة المرجحة (درجة المادة × عدد وحدات المادة)
            weighted_grade = grade.total * course.units
            total_weighted_grades += weighted_grade
            total_units += course.units
    
    # حساب المعدل النهائي
    if total_units > 0:
        return total_weighted_grades / total_units
    else:
        return 0

# التحقق من امتداد الملف
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/data_parser')
@login_required
def data_parser():
    if current_user.user_type != 'instructor':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    return render_template('data_parser.html')

@app.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'غير مصرح لك برفع الملفات'}), 403
    
    try:
        # التحقق من وجود ملف في الطلب
        if 'file' not in request.files:
            app.logger.error("لم يتم تحديد ملف في الطلب")
            return jsonify({'error': 'لم يتم تحديد ملف'}), 400
        
        file = request.files['file']
        
        # التحقق من اختيار ملف
        if file.filename == '':
            app.logger.error("لم يتم اختيار ملف")
            return jsonify({'error': 'لم يتم اختيار ملف'}), 400
        
        # التحقق من امتداد الملف
        if not allowed_file(file.filename):
            app.logger.error(f"امتداد الملف غير مسموح به: {file.filename}")
            return jsonify({'error': 'امتداد الملف غير مسموح به. الامتدادات المسموح بها هي: csv, xlsx, xls'}), 400
        
        # الحصول على نوع الجدول المستهدف
        table_type = request.form.get('table_type')
        if not table_type or table_type not in ['students', 'grades', 'courses']:
            app.logger.error(f"نوع الجدول غير صالح: {table_type}")
            return jsonify({'error': 'نوع الجدول غير صالح'}), 400
        
        # التأكد من وجود مجلد التحميل
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            try:
                os.makedirs(app.config['UPLOAD_FOLDER'])
                app.logger.info(f"تم إنشاء مجلد التحميل: {app.config['UPLOAD_FOLDER']}")
            except Exception as e:
                app.logger.error(f"فشل في إنشاء مجلد التحميل: {str(e)}")
                return jsonify({'error': f'فشل في إنشاء مجلد التحميل: {str(e)}'}), 500
        
        file_path = None
        try:
            # حفظ الملف
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            app.logger.info(f"محاولة حفظ الملف في: {file_path}")
            file.save(file_path)
            app.logger.info(f"تم حفظ الملف بنجاح: {file_path}")
            
            # قراءة الملف باستخدام pandas
            if filename.endswith('.csv'):
                app.logger.info(f"محاولة قراءة ملف CSV: {file_path}")
                df = pd.read_csv(file_path)
            else:
                app.logger.info(f"محاولة قراءة ملف Excel: {file_path}")
                df = pd.read_excel(file_path)
            
            app.logger.info(f"تم قراءة الملف بنجاح، عدد الصفوف: {len(df)}")
            
            # التحقق من أن الملف يحتوي على بيانات
            if df.empty:
                app.logger.error("الملف لا يحتوي على بيانات")
                return jsonify({'error': 'الملف لا يحتوي على بيانات'}), 400
            
            # إعداد معلومات الأعمدة المطلوبة لكل نوع جدول
            required_columns = get_required_columns(table_type)
            
            # التحقق من وجود الأعمدة المطلوبة
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            # تحويل البيانات إلى قاموس
            preview_data = df.head(5).to_dict('records')
            all_data = df.to_dict('records')
            
            # حفظ البيانات في الجلسة للاستخدام لاحقًا
            session['file_data'] = json.dumps(all_data)
            session['table_type'] = table_type
            
            app.logger.info(f"تم تحليل الملف بنجاح: {len(all_data)} صفوف")
            return jsonify({
                'success': True,
                'preview': preview_data,
                'total_rows': len(all_data),
                'columns': df.columns.tolist(),
                'required_columns': required_columns,
                'missing_columns': missing_columns
            })
        
        except pd.errors.EmptyDataError:
            app.logger.error("الملف فارغ أو لا يحتوي على بيانات صالحة")
            return jsonify({'error': 'الملف فارغ أو لا يحتوي على بيانات صالحة'}), 400
        except pd.errors.ParserError:
            app.logger.error("لا يمكن تحليل الملف")
            return jsonify({'error': 'لا يمكن تحليل الملف. تأكد من أن الملف بالتنسيق الصحيح'}), 400
        except Exception as e:
            app.logger.error(f"خطأ في معالجة الملف: {str(e)}")
            return jsonify({'error': f'حدث خطأ أثناء معالجة الملف: {str(e)}'}), 500
        finally:
            # حذف الملف بعد معالجته
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    app.logger.info(f"تم حذف الملف المؤقت: {file_path}")
                except Exception as e:
                    app.logger.error(f"فشل في حذف الملف المؤقت: {str(e)}")
    
    except Exception as e:
        app.logger.error(f"خطأ عام في رفع الملف: {str(e)}")
        return jsonify({'error': f'حدث خطأ غير متوقع: {str(e)}'}), 500

def get_required_columns(table_type):
    """تحديد الأعمدة المطلوبة لكل نوع جدول"""
    if table_type == 'students':
        return ['name', 'username', 'student_id', 'stage']
    elif table_type == 'grades':
        return ['student_id', 'course_id', 'first_attempt', 'second_attempt', 'final_grade']
    elif table_type == 'courses':
        return ['name', 'stage', 'semester']
    return []

@app.route('/import_data', methods=['POST'])
@login_required
def import_data():
    if current_user.user_type != 'instructor':
        app.logger.error(f"محاولة استيراد بيانات من قبل مستخدم غير مصرح له: {current_user.username}")
        return jsonify({'error': 'غير مصرح لك باستيراد البيانات'}), 403
    
    # استرجاع البيانات من الجلسة
    file_data_json = session.get('file_data')
    table_type = session.get('table_type')
    
    app.logger.info(f"محاولة استيراد بيانات من نوع: {table_type}")
    
    if not file_data_json:
        app.logger.error("لم يتم العثور على بيانات الملف في الجلسة")
        return jsonify({'error': 'لم يتم العثور على بيانات الملف للاستيراد'}), 400
    
    if not table_type:
        app.logger.error("لم يتم العثور على نوع الجدول في الجلسة")
        return jsonify({'error': 'لم يتم العثور على نوع الجدول للاستيراد'}), 400
    
    try:
        # تحويل البيانات من JSON إلى قائمة قواميس
        file_data = json.loads(file_data_json)
        app.logger.info(f"تم تحميل البيانات من الجلسة بنجاح، عدد السجلات: {len(file_data)}")
        
        # استيراد البيانات حسب نوع الجدول
        if table_type == 'students':
            app.logger.info("بدء استيراد بيانات الطلاب")
            result = import_students(file_data)
        elif table_type == 'grades':
            app.logger.info("بدء استيراد بيانات الدرجات")
            result = import_grades(file_data)
        elif table_type == 'courses':
            app.logger.info("بدء استيراد بيانات المقررات")
            result = import_courses(file_data)
        else:
            app.logger.error(f"نوع جدول غير صالح: {table_type}")
            return jsonify({'error': 'نوع الجدول غير صالح'}), 400
        
        # حذف البيانات من الجلسة فقط إذا كانت عملية الاستيراد ناجحة
        if result.get('success', False):
            session.pop('file_data', None)
            session.pop('table_type', None)
            app.logger.info("تم حذف بيانات الملف من الجلسة بعد الاستيراد الناجح")
        
        app.logger.info(f"نتيجة الاستيراد: {result.get('success_count', 0)} سجل ناجح، {result.get('error_count', 0)} سجل فاشل")
        return jsonify(result)
    
    except json.JSONDecodeError as e:
        app.logger.error(f"خطأ في تحليل بيانات JSON: {str(e)}")
        return jsonify({'error': f'خطأ في تحليل بيانات الملف: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"خطأ غير متوقع أثناء استيراد البيانات: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء استيراد البيانات: {str(e)}'}), 500

def import_students(data):
    """استيراد بيانات الطلاب"""
    success_count = 0
    error_count = 0
    errors = []
    
    for i, row in enumerate(data):
        try:
            # التحقق من وجود البيانات المطلوبة
            if not all(key in row and row[key] for key in ['name', 'username', 'student_id', 'stage']):
                errors.append({
                    'row': i + 1,
                    'error': 'بيانات غير مكتملة أو فارغة'
                })
                error_count += 1
                continue
            
            # التأكد من أن المرحلة رقم صحيح
            try:
                stage = int(row['stage'])
                if stage < 1 or stage > 4:
                    errors.append({
                        'row': i + 1,
                        'error': f'المرحلة غير صالحة. يجب أن تكون بين 1 و 4'
                    })
                    error_count += 1
                    continue
            except (ValueError, TypeError):
                errors.append({
                    'row': i + 1,
                    'error': f'المرحلة يجب أن تكون رقماً صحيحاً'
                })
                error_count += 1
                continue
            
            # التحقق من عدم وجود اسم مستخدم مكرر
            if User.query.filter_by(username=row['username']).first():
                errors.append({
                    'row': i + 1,
                    'error': f'اسم المستخدم {row["username"]} موجود بالفعل'
                })
                error_count += 1
                continue
            
            # التحقق من عدم وجود رقم طالب مكرر
            if Student.query.filter_by(student_id=row['student_id']).first():
                errors.append({
                    'row': i + 1,
                    'error': f'رقم الطالب {row["student_id"]} موجود بالفعل'
                })
                error_count += 1
                continue
            
            # إنشاء مستخدم جديد
            user = User(
                name=row['name'],
                username=row['username'],
                user_type='student'
            )
            
            # تعيين كلمة مرور افتراضية
            password = row.get('password', 'password')
            user.set_password(password)
            
            db.session.add(user)
            db.session.flush()  # للحصول على معرف المستخدم
            
            # إنشاء طالب جديد
            student = Student(
                user_id=user.id,
                student_id=row['student_id'],
                stage=stage
            )
            
            db.session.add(student)
            success_count += 1
            
        except Exception as e:
            errors.append({
                'row': i + 1,
                'error': str(e)
            })
            error_count += 1
    
    # حفظ التغييرات إذا كانت هناك عمليات ناجحة
    if success_count > 0:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f'حدث خطأ أثناء حفظ البيانات: {str(e)}'
            }
    
    return {
        'success': True,
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors
    }

def import_grades(data):
    """استيراد بيانات الدرجات"""
    success_count = 0
    error_count = 0
    errors = []
    
    for i, row in enumerate(data):
        try:
            # التحقق من وجود البيانات المطلوبة
            if not all(key in row for key in ['student_id', 'course_id']):
                errors.append({
                    'row': i + 1,
                    'error': 'بيانات غير مكتملة'
                })
                error_count += 1
                continue
            
            # البحث عن الطالب
            student = Student.query.filter_by(student_id=row['student_id']).first()
            if not student:
                errors.append({
                    'row': i + 1,
                    'error': f'الطالب برقم {row["student_id"]} غير موجود'
                })
                error_count += 1
                continue
            
            # البحث عن المقرر
            course = Course.query.get(row['course_id'])
            if not course:
                errors.append({
                    'row': i + 1,
                    'error': f'المقرر برقم {row["course_id"]} غير موجود'
                })
                error_count += 1
                continue
            
            # التحقق من عدم وجود درجة مسجلة مسبقًا
            existing_grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
            
            if existing_grade:
                # تحديث الدرجة الموجودة
                if 'first_attempt' in row:
                    existing_grade.first_attempt = row['first_attempt']
                if 'second_attempt' in row:
                    existing_grade.second_attempt = row['second_attempt']
                if 'final_grade' in row:
                    existing_grade.final_grade = row['final_grade']
            else:
                # إنشاء درجة جديدة
                grade = Grade(
                    student_id=student.id,
                    course_id=course.id,
                    first_attempt=row.get('first_attempt'),
                    second_attempt=row.get('second_attempt'),
                    final_grade=row.get('final_grade')
                )
                db.session.add(grade)
            
            success_count += 1
            
        except Exception as e:
            errors.append({
                'row': i + 1,
                'error': str(e)
            })
            error_count += 1
    
    # حفظ التغييرات إذا كانت هناك عمليات ناجحة
    if success_count > 0:
        db.session.commit()
    
    return {
        'success': True,
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors
    }

def import_courses(data):
    """استيراد بيانات المقررات"""
    success_count = 0
    error_count = 0
    errors = []
    
    for i, row in enumerate(data):
        try:
            # التحقق من وجود البيانات المطلوبة
            if not all(key in row for key in ['name', 'stage', 'semester']):
                errors.append({
                    'row': i + 1,
                    'error': 'بيانات غير مكتملة'
                })
                error_count += 1
                continue
            
            # التحقق من عدم وجود مقرر بنفس الاسم والمرحلة والفصل
            existing_course = Course.query.filter_by(
                name=row['name'],
                stage=int(row['stage']),
                semester=int(row['semester'])
            ).first()
            
            if existing_course:
                errors.append({
                    'row': i + 1,
                    'error': f'المقرر {row["name"]} للمرحلة {row["stage"]} والفصل {row["semester"]} موجود بالفعل'
                })
                error_count += 1
                continue
            
            # إنشاء مقرر جديد
            course = Course(
                name=row['name'],
                stage=int(row['stage']),
                semester=int(row['semester'])
            )
            
            db.session.add(course)
            success_count += 1
            
        except Exception as e:
            errors.append({
                'row': i + 1,
                'error': str(e)
            })
            error_count += 1
    
    # حفظ التغييرات إذا كانت هناك عمليات ناجحة
    if success_count > 0:
        db.session.commit()
    
    return {
        'success': True,
        'success_count': success_count,
        'error_count': error_count,
        'errors': errors
    }

# Initialize the database and add initial data
def init_db():
    with app.app_context():
        # Check if database file exists
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'examination.db')
        db_exists = os.path.exists(db_path)
        
        # إنشاء الجداول إذا لم تكن موجودة بالفعل
        db.create_all()
        
        # التحقق من وجود مستخدمين في قاعدة البيانات
        if User.query.count() > 0:
            return  # إذا كان هناك مستخدمين بالفعل، لا تقم بإضافة بيانات افتراضية
            
        # If SQL schema file exists, use it to initialize the database
        if os.path.exists(app.config['SQL_SCHEMA_FILE']):
            # Connect to the database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Read SQL file
            with open(app.config['SQL_SCHEMA_FILE'], 'r', encoding='utf-8') as sql_file:
                sql_script = sql_file.read()
                
            # Execute SQL script
            cursor.executescript(sql_script)
            
            # Commit changes and close connection
            conn.commit()
            conn.close()
            
            print("Database initialized from SQL schema file.")
            return
            
        # If SQL file doesn't exist or couldn't be used, initialize with default data
        # Add instructor
        instructor = User(
            username='instructor',
            name='Dr. محمد أحمد',
            user_type='instructor'
        )
        instructor.set_password('password')
        db.session.add(instructor)
        
        # Add courses
        courses_data = [
            # Stage 1, Semester 1
            {'name': 'اساسيات برمجة', 'stage': 1, 'semester': 1, 'units': 8},
            {'name': 'مقدمة في تكنلوجيا المعلومات', 'stage': 1, 'semester': 1, 'units': 8},
            {'name': 'تصميم منطقي', 'stage': 1, 'semester': 1, 'units': 6},
            {'name': 'اقتصاد', 'stage': 1, 'semester': 1, 'units': 4},
            
            # Stage 1, Semester 2
            {'name': 'هياكل متقطعة', 'stage': 1, 'semester': 2, 'units': 6},
            {'name': 'تركيب الحاسوب', 'stage': 1, 'semester': 2, 'units': 6},
            {'name': 'حقوق الانسان', 'stage': 1, 'semester': 2, 'units': 2},
            {'name': 'ديمقراطية', 'stage': 1, 'semester': 2, 'units': 2},
            
            # Stage 2, Semester 1
            {'name': 'برمجة كيانية', 'stage': 2, 'semester': 1, 'units': 8},
            {'name': 'طرق عددية', 'stage': 2, 'semester': 1, 'units': 6},
            {'name': 'معالجات دقيقة', 'stage': 2, 'semester': 1, 'units': 8},
            {'name': 'اللغة العربية', 'stage': 2, 'semester': 1, 'units': 2},
            
            # Stage 2, Semester 2
            {'name': 'نظرية احتسابية', 'stage': 2, 'semester': 2, 'units': 4},
            {'name': 'هياكل بيانات', 'stage': 2, 'semester': 2, 'units': 8},
            {'name': 'احصاء', 'stage': 2, 'semester': 2, 'units': 4},
            {'name': 'جافا', 'stage': 2, 'semester': 2, 'units': 6},
            
            # Stage 3, Semester 1
            {'name': 'بحث ويب', 'stage': 3, 'semester': 1, 'units': 4},
            {'name': 'برمجة مواقع', 'stage': 3, 'semester': 1, 'units': 6},
            {'name': 'رسم بالحاسوب', 'stage': 3, 'semester': 1, 'units': 8},
            {'name': 'قواعد بيانات', 'stage': 3, 'semester': 1, 'units': 8},
            
            # Stage 3, Semester 2
            {'name': 'مترجمات', 'stage': 3, 'semester': 2, 'units': 6},
            {'name': 'بايثون', 'stage': 3, 'semester': 2, 'units': 6},
            {'name': 'ذكاء اصطناعي', 'stage': 3, 'semester': 2, 'units': 6},
            {'name': 'تشفير', 'stage': 3, 'semester': 2, 'units': 4},
            
            # Stage 4, Semester 1
            {'name': 'انترنيت الاشياء', 'stage': 4, 'semester': 1, 'units': 6},
            {'name': 'نظم تشغيل', 'stage': 4, 'semester': 1, 'units': 8},
            {'name': 'معالجة صور', 'stage': 4, 'semester': 1, 'units': 8},
            {'name': 'امنية حواسيب', 'stage': 4, 'semester': 1, 'units': 4},
            
            # Stage 4, Semester 2
            {'name': 'حوسبة سحابية', 'stage': 4, 'semester': 2, 'units': 4},
            {'name': 'تمييز انماط', 'stage': 4, 'semester': 2, 'units': 4},
            {'name': 'شبكات', 'stage': 4, 'semester': 2, 'units': 8},
            {'name': 'تجارة الكترونية', 'stage': 4, 'semester': 2, 'units': 4},
        ]
        
        for course_data in courses_data:
            course = Course(**course_data)
            db.session.add(course)
        
        # Add sample students
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
            # إضافة 5 طلاب تجريبيين جدد
            {'name': 'مصطفى كاظم', 'username': 'mustafa', 'student_id': 'CS2023004', 'stage': 1},
            {'name': 'ياسمين عادل', 'username': 'yasmin', 'student_id': 'CS2022003', 'stage': 2},
            {'name': 'حسين علي', 'username': 'hussein', 'student_id': 'CS2021003', 'stage': 3},
            {'name': 'رنا محمد', 'username': 'rana', 'student_id': 'CS2020003', 'stage': 4},
            {'name': 'يوسف أحمد', 'username': 'yousef', 'student_id': 'CS2023005', 'stage': 1},
            # إضافة 5 طلاب تجريبيين إضافيين
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
            db.session.flush()  # To get the user ID
            
            student = Student(
                user_id=user.id,
                student_id=student_data['student_id'],
                stage=student_data['stage']
            )
            db.session.add(student)
        
        db.session.commit()
        
        # Add sample grades
        students = Student.query.all()
        courses = Course.query.all()
        
        import random
        for student in students:
            for course in courses:
                if course.stage == student.stage:
                    # Only add grades for the student's current stage
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

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
