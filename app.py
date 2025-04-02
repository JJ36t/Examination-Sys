from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
import os
import sqlite3
import secrets
from datetime import datetime, timedelta
import pandas as pd
import io
import csv
import json
from sqlalchemy import inspect
import xlsxwriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from OpenSSL import crypto

# دالة لحساب تقدير الدرجة بناءً على المجموع
def calculate_grade_evaluation(total):
    if total >= 90:
        return 'امتياز'
    elif total >= 80:
        return 'جيد جداً'
    elif total >= 70:
        return 'جيد'
    elif total >= 60:
        return 'مقبول'
    elif total >= 50:
        return 'ضعيف'
    else:
        return 'راسب'

# تكوين مجلد لتخزين الملفات المرفوعة
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

# التأكد من وجود مجلد التحميل
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# إعداد whitenoise لخدمة الملفات الثابتة في الإنتاج
if 'RENDER' in os.environ:
    try:
        from whitenoise import WhiteNoise
        app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/')
        app.wsgi_app.add_files('static/', prefix='static/')
    except ImportError:
        pass  # تخطي إذا لم تكن مكتبة whitenoise مثبتة
# تكوين قاعدة البيانات مع دعم بيئة الإنتاج
if 'RENDER' in os.environ:
    # على منصة Render
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///examination.db')
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
else:
    # في بيئة التطوير المحلية
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///examination.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQL_SCHEMA_FILE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database_schema.sql')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # تحديد مدة انتهاء الجلسة (30 دقيقة)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'يرجى تسجيل الدخول للوصول إلى هذه الصفحة'
login_manager.login_message_category = 'danger'

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'instructor', 'student', 'admin'
    failed_login_attempts = db.Column(db.Integer, default=0)  # عدد محاولات تسجيل الدخول الفاشلة
    is_locked = db.Column(db.Boolean, default=False)  # حالة حساب المستخدم (مقفل أم لا)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# نموذج للإعدادات
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(200))
    
    @staticmethod
    def get_setting(key, default=None):
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            return setting.value
        return default
    
    @staticmethod
    def set_setting(key, value, description=None):
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
        else:
            setting = Settings(key=key, value=value, description=description)
            db.session.add(setting)
        db.session.commit()
        return True

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
            return "راسب"
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

# دالة تنفذ قبل كل طلب للتحقق من حالة المستخدم
@app.before_request
def check_user_access():
    # قائمة المسارات المسموح بها دون تسجيل دخول
    allowed_paths = ['/', '/login', '/static', '/favicon.ico']
    
    # تحقق إذا كان المسار الحالي مسموحًا به دون تسجيل دخول
    if request.path not in allowed_paths and not request.path.startswith('/static/'):
        if not current_user.is_authenticated:
            # إعادة توجيه المستخدم إلى صفحة تسجيل الدخول إذا لم يكن مسجلاً الدخول
            flash('يرجى تسجيل الدخول للوصول إلى هذه الصفحة', 'danger')
            return redirect(url_for('login'))
        
        # التحقق من تطابق نوع المستخدم مع المسار المطلوب
        if current_user.user_type == 'student' and '/admin/' in request.path:
            flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
            return redirect(url_for('student_dashboard'))
        
        if current_user.user_type == 'instructor' and '/admin/' in request.path:
            flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
            return redirect(url_for('instructor_dashboard'))
        
        if current_user.user_type == 'admin' and request.path.startswith('/student_dashboard'):
            flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
            return redirect(url_for('admin_dashboard'))
            
    # تعيين خاصية تجديد الجلسة
    if current_user.is_authenticated:
        session.permanent = True

# Routes
@app.route('/')
def index():
    # التوجيه دائمًا إلى صفحة تسجيل الدخول بغض النظر عن حالة المستخدم
    return redirect(url_for('login'))

# مسار فحص صحة التطبيق لمنصة Render
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    # تسجيل الخروج من أي حساب قد يكون مفتوحًا حاليًا
    if current_user.is_authenticated:
        logout_user()
        flash('تم تسجيل الخروج من الجلسة السابقة', 'info')
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        
        # التحقق من وجود جميع البيانات المطلوبة
        if not username or not password or not user_type:
            flash('جميع الحقول مطلوبة', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        # التحقق مما إذا كان الحساب مقفلاً بسبب محاولات متعددة فاشلة
        if user and user.is_locked:
            flash('تم قفل الحساب بسبب كثرة محاولات تسجيل الدخول الفاشلة. يرجى التواصل مع الإدارة.', 'danger')
            return render_template('login.html', show_reset_request=True, username=username)
        
        if user and user.check_password(password) and user.user_type == user_type:
            # نجاح تسجيل الدخول، إعادة تعيين عدد المحاولات الفاشلة
            user.failed_login_attempts = 0
            db.session.commit()
            
            # تعيين الجلسة على أنها دائمة ولكن مع وقت انتهاء صلاحية محدد
            session.permanent = True
            
            login_user(user)
            # التوجيه بناءً على نوع المستخدم
            if user.user_type == 'admin':
                session['active_page'] = 'admin_dashboard'
                return redirect(url_for('admin_dashboard'))
            elif user.user_type == 'instructor':
                session['active_page'] = 'instructor_dashboard'
                return redirect(url_for('instructor_dashboard'))
            else:  # student
                session['active_page'] = 'student_dashboard'
                return redirect(url_for('student_dashboard'))
        else:
            # فشل تسجيل الدخول
            if user:
                # زيادة عدد المحاولات الفاشلة
                user.failed_login_attempts += 1
                
                # إذا تجاوز عدد المحاولات الفاشلة 5، قم بقفل الحساب
                if user.failed_login_attempts >= 5:
                    user.is_locked = True
                    flash('تم قفل الحساب بسبب كثرة محاولات تسجيل الدخول الفاشلة. يرجى التواصل مع الإدارة.', 'danger')
                else:
                    attempts_left = 5 - user.failed_login_attempts
                    flash(f'خطأ في اسم المستخدم أو كلمة المرور أو نوع المستخدم. محاولات متبقية: {attempts_left}', 'danger')
                
                db.session.commit()
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
    
    # تخزين معلومات الصفحة الحالية في الجلسة
    session['active_page'] = 'instructor_dashboard'
    
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
    
    # تخزين معلومات الصفحة الحالية في الجلسة
    session['active_page'] = 'student_dashboard'
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash('لم يتم العثور على بيانات الطالب', 'danger')
        return redirect(url_for('login'))
    
    # ترتيب المراحل بحيث تأتي المرحلة الحالية للطالب أولاً، ثم المراحل السابقة، ثم المراحل المستقبلية
    current_stage = student.stage
    stages = []
    
    # إضافة المرحلة الحالية أولاً
    stages.append(current_stage)
    
    # إضافة المراحل السابقة بترتيب تنازلي
    for stage in range(current_stage-1, 0, -1):
        stages.append(stage)
    
    # إضافة المراحل المستقبلية
    for stage in range(current_stage+1, 5):
        stages.append(stage)
        
    semesters = [1, 2]
    
    all_grades = {}
    stage_gpas = {}  # لتخزين المعدل النهائي لكل مرحلة
    
    # معلومات إضافية حول الطالب لعرضها في الواجهة
    student_info = {
        'name': current_user.name,
        'id': student.student_id,
        'current_stage': current_stage
    }
    
    for stage in stages:
        all_grades[stage] = {}
        
        # حساب المعدل النهائي للمرحلة - يمكن أن يكون رقماً أو نصاً "راسب"
        try:
            stage_gpas[stage] = calculate_stage_gpa(student.id, stage)
        except Exception as e:
            app.logger.error(f"خطأ في حساب معدل المرحلة {stage}: {str(e)}")
            # في حالة حدوث خطأ، استخدم قيمة افتراضية
            stage_gpas[stage] = 0
        
        for semester in semesters:
            semester_grades = []
            try:
                courses = Course.query.filter_by(stage=stage, semester=semester).all()
                for course in courses:
                    grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
                    if grade:
                        semester_grades.append({
                            'course': course,
                            'grade': grade
                        })
            except Exception as e:
                app.logger.error(f"خطأ في جلب درجات الكورس {semester} للمرحلة {stage}: {str(e)}")
            
            all_grades[stage][semester] = semester_grades
    
    return render_template('student_dashboard.html', 
                           all_grades=all_grades, 
                           stages=stages, 
                           semesters=semesters, 
                           stage_gpas=stage_gpas, 
                           student_info=student_info)

@app.route('/get_students_by_stage_semester', methods=['POST'])
@login_required
def get_students_by_stage_semester():
    if current_user.user_type != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    stage = request.form.get('stage')
    semester = request.form.get('semester')
    
    if not stage or not semester:
        return jsonify({'error': 'Missing parameters'}), 400
    
    # تحويل المعلمات إلى أرقام
    stage = int(stage)
    semester = int(semester)
    
    # تعديل هنا: جلب الطلاب في المرحلة المحددة فقط
    students = Student.query.filter_by(stage=stage).all()
    
    # جلب المواد الدراسية للمرحلة والكورس المحددين
    if semester == 1:
        courses = Course.query.filter_by(stage=stage, semester=semester).all()
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
        
        student_data = {
            'id': student.id,
            'name': user.name,
            'student_id': student.student_id,
            'grades': [],
            'semester_gpa': semester_gpa,
            'stage_gpa': stage_gpa,
            'has_failed_courses': False  # قيمة افتراضية، سيتم تحديثها لاحقاً
        }
        
        for course in courses:
            grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
            if grade:
                # التحقق مما إذا كان الطالب راسباً في هذه المادة
                total_grade = grade.total
                if total_grade < 50:
                    student_data['has_failed_courses'] = True
                
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
            'grades': [],
            'has_failed_courses': False  # قيمة افتراضية، سيتم تحديثها لاحقاً
        }
        
        for course in courses:
            grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
            if grade:
                # التحقق مما إذا كان الطالب راسباً في هذه المادة
                total_grade = grade.total
                if total_grade < 50:
                    student_data['has_failed_courses'] = True
                
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

@app.route('/api/admin/courses', methods=['GET', 'POST'])
@login_required
def get_courses():
    if current_user.user_type != 'instructor' and current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # الحصول على المعلمات من النموذج أو معلمات الاستعلام
    stage = request.form.get('stage') or request.args.get('stage')
    semester = request.form.get('semester') or request.args.get('semester')
    search = request.form.get('search') or request.args.get('search', '')
    
    # التحقق من وجود معلمات المرحلة والفصل
    if not stage or not semester:
        # إذا كان الطلب للبحث، فلا نشترط توفر المرحلة والفصل
        if request.args.get('search'):
            courses = Course.query
            if search:
                courses = courses.filter(Course.name.ilike(f'%{search}%'))
        else:
            return jsonify({'error': 'المعلمات مفقودة - يرجى تحديد المرحلة والفصل'}), 400
    else:
        # البحث عن المقررات بالمرحلة والفصل
        courses = Course.query.filter_by(stage=stage, semester=semester)
        if search:
            courses = courses.filter(Course.name.ilike(f'%{search}%'))
    
    # تنفيذ الاستعلام
    courses = courses.all()
    
    # بناء النتيجة
    result = []
    for course in courses:
        result.append({
            'id': course.id,
            'name': course.name,
            'stage': course.stage,
            'semester': course.semester,
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
            'semester_gpa': semester_gpa,
            'stage_gpa': stage_gpa,
            'has_failed_courses': failed_courses > 0
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
            'semester_gpa': calculate_semester_gpa(student.id, stage, semester),
            'stage_gpa': calculate_stage_gpa(student.id, stage) if stage else None,
            'has_failed_courses': failed_courses > 0
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
    stage = request.form.get('stage', '1')  # استلام المرحلة من النموذج، ووضع المرحلة الأولى كقيمة افتراضية
    
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
    
    if last_student and last_student.student_id:
        # استخراج الرقم من معرف الطالب إذا كان يحتوي على أرقام فقط
        try:
            # استخراج الرقم التسلسلي (آخر 3 أرقام)
            sequence_number = int(last_student.student_id[-3:])
            new_sequence_number = sequence_number + 1
            student_id = f"{year_prefix}{new_sequence_number:03d}"
        except (ValueError, IndexError):
            # إذا كان هناك خطأ في تنسيق الرقم، ابدأ من 001
            student_id = f"{year_prefix}001"
    else:
        # إذا لم يكن هناك طلاب بالفعل، ابدأ من 001
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
            stage=int(stage)  # استخدام المرحلة المحددة من النموذج
        )
        db.session.add(student)
        success_count = 1
        
        # إنشاء سجلات درجات فارغة للطالب
        courses = Course.query.filter_by(stage=int(stage)).all()  # استخدام المرحلة المحددة بدلاً من الافتراضية
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
    if current_user.user_type not in ['instructor', 'admin']:
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
    if current_user.user_type not in ['instructor', 'admin']:
        return jsonify({'error': 'غير مصرح لك بالوصول إلى هذه البيانات'}), 403
    
    search_term = request.form.get('search_term', '')
    if not search_term:
        return jsonify([])
    
    # البحث في اسم الطالب ورقم الطالب واسم المستخدم
    students = []
    
    # البحث في جدول المستخدمين (الاسم واسم المستخدم)
    users = User.query.filter(
        (User.user_type == 'student') & 
        ((User.name.like(f'%{search_term}%') | User.username.like(f'%{search_term}%')))
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
        
        # حفظ المرحلة القديمة قبل التحديث
        old_stage = student.stage
        
        student.student_id = student_id_number
        student.stage = int(stage)
        
        # إذا تغيرت المرحلة، نقوم بإنشاء سجلات درجات جديدة للمقررات في المرحلة الجديدة
        if old_stage != int(stage):
            # الحصول على المقررات في المرحلة الجديدة
            new_stage_courses = Course.query.filter_by(stage=int(stage)).all()
            
            # إنشاء سجلات درجات فارغة للطالب في المقررات الجديدة
            current_year = datetime.now().year
            for course in new_stage_courses:
                # التحقق من عدم وجود سجل درجات للطالب في هذا المقرر
                existing_grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
                if not existing_grade:
                    grade = Grade(
                        student_id=student.id,
                        course_id=course.id,
                        coursework=0,
                        final_exam=0,
                        decision_marks=0,
                        academic_year=f"{current_year-1}/{current_year+1}"
                    )
                    db.session.add(grade)
        
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
    
    إذا كان الطالب راسباً في أي مادة، يتم إرجاع "راسب" بدلاً من المعدل
    """
    # جلب جميع المقررات للمرحلة المحددة
    courses = Course.query.filter_by(stage=stage).all()
    
    if not courses:
        return 0
    
    total_weighted_grades = 0
    total_units = 0
    has_failed_course = False
    
    for course in courses:
        # جلب درجة الطالب لهذا المقرر
        grade = Grade.query.filter_by(student_id=student_id, course_id=course.id).first()
        
        if grade:
            # التحقق مما إذا كان الطالب راسباً في هذه المادة
            if grade.total < 50:
                has_failed_course = True
            
            # حساب الدرجة المرجحة (درجة المادة × عدد وحدات المادة)
            weighted_grade = grade.total * course.units
            total_weighted_grades += weighted_grade
            total_units += course.units
    
    # إذا كان الطالب راسباً في أي مادة، أرجع "راسب" بدلاً من المعدل
    if has_failed_course:
        return "راسب"
    
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
    
    إذا كان الطالب راسباً في أي مادة في الكورس الثاني، يتم إرجاع "راسب" بدلاً من المعدل
    """
    # جلب جميع المقررات للمرحلة والكورس المحددين
    courses = Course.query.filter_by(stage=stage, semester=semester).all()
    
    if not courses:
        return 0
    
    total_weighted_grades = 0
    total_units = 0
    has_failed_course = False
    
    for course in courses:
        # جلب درجة الطالب لهذا المقرر
        grade = Grade.query.filter_by(student_id=student_id, course_id=course.id).first()
        
        if grade:
            # التحقق مما إذا كان الطالب راسباً في هذه المادة وفي الكورس الثاني
            if semester == 2 and grade.total < 50:
                has_failed_course = True
            
            # حساب الدرجة المرجحة (درجة المادة × عدد وحدات المادة)
            weighted_grade = grade.total * course.units
            total_weighted_grades += weighted_grade
            total_units += course.units
    
    # إذا كان الطالب راسباً في أي مادة من الكورس الثاني، أرجع "راسب" بدلاً من المعدل
    if has_failed_course:
        return "راسب"
    
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
        flash('غير مصرح لك برفع الملفات', 'danger')
        return redirect(url_for('login'))
    
    try:
        # التحقق من وجود ملف في الطلب
        if 'file' not in request.files:
            app.logger.error("لم يتم تحديد ملف في الطلب")
            flash('لم يتم تحديد ملف', 'danger')
            return redirect(url_for('data_parser'))
        
        file = request.files['file']
        
        # التحقق من اختيار ملف
        if file.filename == '':
            app.logger.error("لم يتم اختيار ملف")
            flash('لم يتم اختيار ملف', 'danger')
            return redirect(url_for('data_parser'))
        
        # التحقق من امتداد الملف
        if not allowed_file(file.filename):
            app.logger.error(f"امتداد الملف غير مسموح به: {file.filename}")
            flash('امتداد الملف غير مسموح به. الامتدادات المسموح بها هي: csv, xlsx, xls', 'danger')
            return redirect(url_for('data_parser'))
        
        # الحصول على نوع الجدول المستهدف
        table_type = request.form.get('table_type')
        if not table_type or table_type not in ['students', 'grades', 'courses']:
            app.logger.error(f"نوع جدول غير صالح: {table_type}")
            flash('نوع الجدول غير صالح', 'danger')
            return redirect(url_for('data_parser'))
        
        # التأكد من وجود مجلد التحميل
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            try:
                os.makedirs(app.config['UPLOAD_FOLDER'])
                app.logger.info(f"تم إنشاء مجلد التحميل: {app.config['UPLOAD_FOLDER']}")
            except Exception as e:
                app.logger.error(f"فشل في إنشاء مجلد التحميل: {str(e)}")
                flash(f'فشل في إنشاء مجلد التحميل: {str(e)}', 'danger')
                return redirect(url_for('data_parser'))
        
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
                flash('الملف لا يحتوي على بيانات', 'danger')
                return redirect(url_for('data_parser'))
            
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
            
            # عرض البيانات في القالب
            return render_template('data_parser.html', 
                                preview_data=preview_data,
                                total_rows=len(all_data),
                                columns=df.columns.tolist(),
                                required_columns=required_columns,
                                missing_columns=missing_columns)
        
        except pd.errors.EmptyDataError:
            app.logger.error("الملف فارغ أو لا يحتوي على بيانات صالحة")
            flash('الملف فارغ أو لا يحتوي على بيانات صالحة', 'danger')
            return redirect(url_for('data_parser'))
        except pd.errors.ParserError:
            app.logger.error("لا يمكن تحليل الملف")
            flash('لا يمكن تحليل الملف. تأكد من أن الملف بالتنسيق الصحيح', 'danger')
            return redirect(url_for('data_parser'))
        except Exception as e:
            app.logger.error(f"خطأ في معالجة الملف: {str(e)}")
            flash(f'حدث خطأ أثناء معالجة الملف: {str(e)}', 'danger')
            return redirect(url_for('data_parser'))
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
        flash(f'حدث خطأ غير متوقع: {str(e)}', 'danger')
        return redirect(url_for('data_parser'))

@app.route('/import_data', methods=['POST'])
@login_required
def import_data():
    if current_user.user_type != 'instructor':
        app.logger.error(f"محاولة استيراد بيانات من قبل مستخدم غير مصرح له: {current_user.username}")
        flash('غير مصرح لك باستيراد البيانات', 'danger')
        return redirect(url_for('data_parser'))
    
    # استرجاع البيانات من الجلسة
    file_data_json = session.get('file_data')
    table_type = session.get('table_type')
    
    app.logger.info(f"محاولة استيراد بيانات من نوع: {table_type}")
    
    if not file_data_json:
        app.logger.error("لم يتم العثور على بيانات الملف في الجلسة")
        flash('لم يتم العثور على بيانات الملف للاستيراد', 'danger')
        return redirect(url_for('data_parser'))
    
    if not table_type:
        app.logger.error("لم يتم العثور على نوع الجدول في الجلسة")
        flash('لم يتم العثور على نوع الجدول للاستيراد', 'danger')
        return redirect(url_for('data_parser'))
    
    try:
        # تحويل البيانات من JSON إلى قائمة قواميس
        file_data = json.loads(file_data_json)
        app.logger.info(f"تم تحميل البيانات من الجلسة بنجاح، عدد السجلات: {len(file_data)}")
        
        # تسجيل نمذوج البيانات للتصحيح
        if len(file_data) > 0:
            app.logger.info(f"نموذج من البيانات: {file_data[0]}")
        
        # استيراد البيانات حسب نوع الجدول
        if table_type == 'students':
            app.logger.info("بدء استيراد بيانات الطلاب")
            result = import_students(file_data)
            app.logger.info(f"نتيجة استيراد الطلاب: {result}")
        elif table_type == 'grades':
            app.logger.info("بدء استيراد بيانات الدرجات")
            result = import_grades(file_data)
        elif table_type == 'courses':
            app.logger.info("بدء استيراد بيانات المقررات")
            result = import_courses(file_data)
        else:
            app.logger.error(f"نوع جدول غير صالح: {table_type}")
            flash('نوع الجدول غير صالح', 'danger')
            return redirect(url_for('data_parser'))
        
        # حذف البيانات من الجلسة بعد الاستيراد
        session.pop('file_data', None)
        session.pop('table_type', None)
        app.logger.info("تم حذف بيانات الملف من الجلسة بعد الاستيراد")
        
        app.logger.info(f"نتيجة الاستيراد: {result.get('success_count', 0)} سجل ناجح، {result.get('error_count', 0)} سجل فاشل")
        
        # إضافة رسالة نجاح
        if result.get('success_count', 0) > 0:
            flash(f'تم استيراد {result.get("success_count")} سجل بنجاح', 'success')
        else:
            flash('لم يتم استيراد أي سجلات. تحقق من سجل الأخطاء.', 'warning')
        
        # عرض نتائج الاستيراد
        return render_template('data_parser.html', import_results=result)
    
    except json.JSONDecodeError as e:
        app.logger.error(f"خطأ في تحليل بيانات JSON: {str(e)}")
        flash(f'خطأ في تحليل بيانات الملف: {str(e)}', 'danger')
        return redirect(url_for('data_parser'))
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء استيراد البيانات: {str(e)}'}), 500

def get_required_columns(table_type):
    """تحديد الأعمدة المطلوبة لكل نوع جدول"""
    if table_type == 'students':
        return ['name', 'username', 'student_id', 'stage']
    elif table_type == 'grades':
        return ['student_id', 'course_id', 'coursework', 'final_exam', 'decision_marks']
    elif table_type == 'courses':
        return ['name', 'stage', 'semester', 'units']
    return []

def import_students(data):
    """استيراد بيانات الطلاب"""
    app.logger.info(f"بدء استيراد الطلاب، عدد السجلات المستلمة: {len(data)}")
    success_count = 0
    error_count = 0
    errors = []
    
    # دالة مساعدة لتوليد رقم طالب جديد
    def generate_student_id():
        # البحث عن آخر طالب في قاعدة البيانات
        latest_student = Student.query.order_by(Student.id.desc()).first()
        
        if latest_student and latest_student.student_id:
            # استخراج الرقم من معرف الطالب إذا كان يحتوي على أرقام فقط
            try:
                # استخراج الرقم التسلسلي (آخر 3 أرقام)
                sequence_number = int(latest_student.student_id[-3:])
                new_sequence_number = sequence_number + 1
                student_id = f"{latest_student.student_id[:-3]}{new_sequence_number:03d}"
            except (ValueError, IndexError):
                # إذا كان هناك خطأ في تنسيق الرقم، ابدأ من 001
                student_id = f"{latest_student.student_id[:-3]}001"
        else:
            # إذا لم يكن هناك طلاب بالفعل، ابدأ من 001
            student_id = "CS2023001"
        
        return student_id
    
    for i, row in enumerate(data):
        try:
            app.logger.info(f"معالجة السجل {i+1}: {row}")
            # التحقق من وجود البيانات المطلوبة (باستثناء student_id الذي يمكن توليده تلقائياً)
            required_fields = ['name', 'username', 'stage']
            if not all(key in row and str(row[key]).strip() for key in required_fields):
                missing_keys = [key for key in required_fields if key not in row or not str(row[key]).strip()]
                app.logger.error(f"بيانات غير مكتملة في السجل {i+1}: الحقول المفقودة: {missing_keys}")
                errors.append({
                    'row': i + 1,
                    'error': f'بيانات غير مكتملة أو فارغة. الحقول المفقودة: {missing_keys}'
                })
                error_count += 1
                continue
            
            # التأكد من أن المرحلة رقم صحيح
            try:
                stage = int(float(row['stage']))
                if stage < 1 or stage > 4:
                    app.logger.error(f"المرحلة غير صالحة في السجل {i+1}: {stage}")
                    errors.append({
                        'row': i + 1,
                        'error': f'المرحلة غير صالحة. يجب أن تكون بين 1 و 4'
                    })
                    error_count += 1
                    continue
            except (ValueError, TypeError) as e:
                app.logger.error(f"خطأ في تحويل المرحلة في السجل {i+1}: {str(e)}")
                errors.append({
                    'row': i + 1,
                    'error': f'المرحلة يجب أن تكون رقماً صحيحاً: {str(e)}'
                })
                error_count += 1
                continue
            
            # تنظيف البيانات
            student_name = str(row['name']).strip()
            student_username = str(row['username']).strip()
            
            # التحقق من رقم الطالب وتوليده إذا كان فارغاً أو nan
            student_id = row.get('student_id', '')
            # التحقق من قيمة NaN باستخدام pandas
            if pd.isna(student_id) or str(student_id).strip() == '' or str(student_id).lower().strip() == 'nan':
                student_id = generate_student_id()
                app.logger.info(f"تم توليد رقم طالب تلقائياً للسجل {i+1}: {student_id}")
            else:
                student_id = str(student_id).strip()
            
            # التحقق من عدم وجود اسم مستخدم مكرر
            if User.query.filter_by(username=student_username).first():
                app.logger.error(f"اسم المستخدم موجود بالفعل في السجل {i+1}: {student_username}")
                errors.append({
                    'row': i + 1,
                    'error': f'اسم المستخدم {student_username} موجود بالفعل'
                })
                error_count += 1
                continue
            
            # التحقق من عدم وجود رقم طالب مكرر
            if Student.query.filter_by(student_id=student_id).first():
                app.logger.error(f"رقم الطالب موجود بالفعل في السجل {i+1}: {student_id}")
                errors.append({
                    'row': i + 1,
                    'error': f'رقم الطالب {student_id} موجود بالفعل'
                })
                error_count += 1
                continue
            
            # إنشاء مستخدم جديد
            user = User(
                username=student_username,
                name=student_name,
                user_type='student'
            )
            
            # تعيين كلمة مرور افتراضية
            password = str(row.get('password', 'password')).strip()
            user.set_password(password)
            
            app.logger.info(f"إضافة مستخدم جديد: {student_name}, {student_username}")
            db.session.add(user)
            db.session.flush()  # للحصول على معرف المستخدم
            
            # إنشاء طالب جديد
            student = Student(
                user_id=user.id,
                student_id=student_id,
                stage=stage
            )
            
            app.logger.info(f"إضافة طالب جديد: ID={student_id}, المرحلة={stage}")
            db.session.add(student)
            success_count += 1
            
        except Exception as e:
            app.logger.error(f"خطأ غير متوقع في السجل {i+1}: {str(e)}")
            errors.append({
                'row': i + 1,
                'error': str(e)
            })
            error_count += 1
    
    # حفظ التغييرات إذا كانت هناك عمليات ناجحة
    if success_count > 0:
        try:
            app.logger.info(f"محاولة حفظ {success_count} طالب إلى قاعدة البيانات")
            db.session.commit()
            app.logger.info("تم حفظ البيانات بنجاح")
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'success_count': 0,
                'error_count': error_count + success_count,
                'errors': errors + [{'row': 'ALL', 'error': f'حدث خطأ أثناء حفظ البيانات: {str(e)}'}]
            }
    else:
        app.logger.info("لم تتم إضافة أي طالب")
    
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
    current_year = datetime.now().year
    academic_year = f"{current_year-1}/{current_year}"
    
    for i, row in enumerate(data):
        try:
            # التحقق من وجود البيانات المطلوبة
            if not all(key in row for key in ['student_id', 'course_id', 'coursework', 'final_exam']):
                errors.append({
                    'row': i + 1,
                    'error': 'بيانات غير مكتملة، يجب توفير (رقم الطالب، رقم المقرر، درجة أعمال الفصل، درجة الامتحان النهائي)'
                })
                error_count += 1
                continue
            
            # البحث عن الطالب
            student = Student.query.filter_by(student_id=str(row['student_id'])).first()
            if not student:
                errors.append({
                    'row': i + 1,
                    'error': f'الطالب برقم {row["student_id"]} غير موجود'
                })
                error_count += 1
                continue
            
            # البحث عن المقرر باستخدام المعرف المقدم
            course = Course.query.get(int(row['course_id']))
            if not course:
                errors.append({
                    'row': i + 1,
                    'error': f'المقرر برقم {row["course_id"]} غير موجود'
                })
                error_count += 1
                continue
            
            # التحقق من أن الطالب في نفس مرحلة المقرر
            if student.stage != course.stage:
                errors.append({
                    'row': i + 1,
                    'error': f'الطالب في المرحلة {student.stage} بينما المقرر في المرحلة {course.stage}'
                })
                error_count += 1
                continue
            
            # التحقق من صلاحية الدرجات
            try:
                coursework = int(row['coursework'])
                final_exam = int(row['final_exam'])
                decision_marks = int(row.get('decision_marks', 0))
                
                if not (0 <= coursework <= 50):
                    errors.append({
                        'row': i + 1,
                        'error': f'درجة أعمال الفصل {coursework} خارج النطاق المسموح (0-50)'
                    })
                    error_count += 1
                    continue
                
                if not (0 <= final_exam <= 50):
                    errors.append({
                        'row': i + 1,
                        'error': f'درجة الامتحان النهائي {final_exam} خارج النطاق المسموح (0-50)'
                    })
                    error_count += 1
                    continue
                
                if not (0 <= decision_marks <= 10):
                    errors.append({
                        'row': i + 1,
                        'error': f'درجة القرار {decision_marks} خارج النطاق المسموح (0-10)'
                    })
                    error_count += 1
                    continue
            except ValueError:
                errors.append({
                    'row': i + 1,
                    'error': 'تنسيق الدرجات غير صحيح، يجب أن تكون أرقامًا صحيحة'
                })
                error_count += 1
                continue
            
            # التحقق من عدم وجود درجة مسجلة مسبقًا
            existing_grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
            
            if existing_grade:
                # تحديث الدرجة الموجودة
                existing_grade.coursework = coursework
                existing_grade.final_exam = final_exam
                existing_grade.decision_marks = decision_marks
                existing_grade.academic_year = academic_year
            else:
                # إنشاء درجة جديدة
                grade = Grade(
                    student_id=student.id,
                    course_id=course.id,
                    coursework=coursework,
                    final_exam=final_exam,
                    decision_marks=decision_marks,
                    academic_year=academic_year
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
            if not all(key in row for key in ['name', 'stage', 'semester', 'units']):
                errors.append({
                    'row': i + 1,
                    'error': 'بيانات غير مكتملة'
                })
                error_count += 1
                continue
            
            # التحقق من عدم وجود مقرر بنفس الاسم والمرحلة والفصل
            existing_course = Course.query.filter(
                Course.name == row['name'],
                Course.stage == int(row['stage']),
                Course.semester == int(row['semester'])
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
                semester=int(row['semester']),
                units=int(row['units'])
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
        
        # Add admin
        admin = User(
            username='admin',
            name='Admin',
            user_type='admin'
        )
        admin.set_password('password')
        db.session.add(admin)
        
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

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    # جلب إحصاءات للوحة التحكم
    total_students = Student.query.count()
    total_courses = Course.query.count()
    total_users = User.query.count()
    
    # إحصاءات الطلاب حسب المرحلة
    students_per_stage = []
    for stage in range(1, 5):
        count = Student.query.filter_by(stage=stage).count()
        students_per_stage.append(count)
    
    return render_template('admin_dashboard.html', 
                           active_page='dashboard',
                           total_students=total_students,
                           total_courses=total_courses,
                           total_users=total_users,
                           students_per_stage=students_per_stage)

@app.route('/api/admin/stats')
@login_required
def admin_api_stats():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # إحصاءات أساسية
    stats = {
        'students': Student.query.count(),
        'courses': Course.query.count(),
        'active_users': User.query.count(),
        'students_per_stage': [],
    }
    
    # إحصاءات الطلاب حسب المرحلة
    for stage in range(1, 5):
        count = Student.query.filter_by(stage=stage).count()
        stats['students_per_stage'].append(count)
    
    # آخر النشاطات (يمكن إضافة جدول للنشاطات لاحقًا)
    stats['activities'] = [
        {'user': 'النظام', 'action': 'تم تسجيل الدخول إلى لوحة التحكم', 'time': datetime.now().strftime('%Y-%m-%d %H:%M')}
    ]
    
    return jsonify(stats)

@app.route('/create_admin', methods=['GET', 'POST'])
@login_required
def create_admin():
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بإنشاء حساب مدير', 'danger')
        return redirect(url_for('login'))
    
    form = AdminRegistrationForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data,
            username=form.username.data,
            user_type='admin'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('تم إنشاء حساب المدير بنجاح', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('create_admin.html', title='إنشاء حساب مدير', form=form)

@app.route('/initialize_admin', methods=['GET', 'POST'])
def initialize_admin():
    # التحقق من عدم وجود حساب مدير
    admin_exists = User.query.filter_by(user_type='admin').first() is not None
    if admin_exists:
        flash('تم إنشاء حساب مدير بالفعل', 'warning')
        return redirect(url_for('login'))
    
    form = AdminRegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            name=form.name.data,
            user_type='admin'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('تم إنشاء حساب المدير الأول بنجاح', 'success')
        return redirect(url_for('login'))
    
    return render_template('initialize_admin.html', title='إنشاء حساب المدير الأول', form=form)

# نماذج للاستخدام في النماذج
class LoginForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    remember_me = BooleanField('تذكرني')
    submit = SubmitField('تسجيل الدخول')

class AdminRegistrationForm(FlaskForm):
    name = StringField('الاسم الكامل', validators=[DataRequired()])
    username = StringField('اسم المستخدم', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    confirm_password = PasswordField(
        'تأكيد كلمة المرور', 
        validators=[DataRequired(), EqualTo('password', message='يجب أن تتطابق كلمات المرور')]
    )
    submit = SubmitField('إنشاء حساب')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('اسم المستخدم موجود بالفعل، الرجاء اختيار اسم آخر')

@app.route('/create_default_admin')
def create_default_admin():
    # التحقق من وجود حساب مدير
    admin_exists = User.query.filter_by(user_type='admin').first() is not None
    
    if not admin_exists:
        # إنشاء حساب مدير جديد
        admin = User(
            username='admin',
            name='Admin',
            user_type='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        flash('تم إنشاء حساب المدير بنجاح. اسم المستخدم: admin، كلمة المرور: admin123', 'success')
    else:
        flash('حساب المدير موجود بالفعل', 'info')
    
    return redirect(url_for('login'))

@app.route('/admin/students')
@login_required
def admin_students():
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    return render_template('admin_students.html', active_page='students')

@app.route('/admin/courses')
@login_required
def admin_courses():
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    return render_template('admin_courses.html', active_page='courses')

@app.route('/admin/grades')
@login_required
def admin_grades():
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    return render_template('admin_grades.html', active_page='grades')

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    return render_template('admin_users.html', active_page='users')

@app.route('/admin/reports')
@login_required
def admin_reports():
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    return render_template('admin_reports.html', active_page='reports')

@app.route('/admin/export_data')
@login_required
def admin_export_data():
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    return render_template('admin_export_data.html', active_page='export_data')

@app.route('/admin/settings')
@login_required
def admin_settings():
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    # التحقق من وجود جدول الإعدادات وإنشائه إذا لم يكن موجوداً
    initialize_settings()
    
    settings = {}
    all_settings = Settings.query.all()
    for setting in all_settings:
        settings[setting.key] = setting.value
    
    return render_template('admin_settings.html', active_page='settings', settings=settings)

@app.route('/api/admin/settings', methods=['GET'])
@login_required
def get_settings():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # جلب جميع الإعدادات
    settings = {}
    all_settings = Settings.query.all()
    for setting in all_settings:
        settings[setting.key] = {
            'value': setting.value,
            'description': setting.description
        }
    
    return jsonify(settings)

@app.route('/api/admin/settings/update', methods=['POST'])
@login_required
def update_settings():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # استلام بيانات الإعدادات
        settings_data = request.json
        
        # تحديث الإعدادات
        for key, value in settings_data.items():
            Settings.set_setting(key, value)
        
        return jsonify({'success': True, 'message': 'تم تحديث الإعدادات بنجاح'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/backup', methods=['GET'])
@login_required
def backup_database():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # إنشاء نسخة احتياطية من البيانات
        students = Student.query.all()
        courses = Course.query.all()
        grades = Grade.query.all()
        users = User.query.filter(User.user_type != 'admin').all()
        settings = Settings.query.all()
        
        backup_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'students': [],
            'courses': [],
            'grades': [],
            'users': [],
            'settings': []
        }
        
        # تخزين بيانات الطلاب
        for student in students:
            user = User.query.get(student.user_id)
            
            backup_data['students'].append({
                'student_id': student.student_id,
                'name': user.name,
                'username': user.username,
                'stage': student.stage
            })
        
        # تخزين بيانات المقررات
        for course in courses:
            backup_data['courses'].append({
                'name': course.name,
                'stage': course.stage,
                'semester': course.semester,
                'units': course.units
            })
        
        # تخزين بيانات الدرجات
        for grade in grades:
            student = Student.query.get(grade.student_id)
            course = Course.query.get(grade.course_id)
            backup_data['grades'].append({
                'student_id': student.student_id if student else None,
                'course_name': course.name if course else None,
                'coursework': grade.coursework,
                'final_exam': grade.final_exam,
                'decision_marks': grade.decision_marks,
                'academic_year': grade.academic_year
            })
        
        # تخزين بيانات المستخدمين (بدون كلمات المرور)
        for user in users:
            backup_data['users'].append({
                'username': user.username,
                'name': user.name,
                'user_type': user.user_type
            })
        
        # تخزين الإعدادات
        for setting in settings:
            backup_data['settings'].append({
                'key': setting.key,
                'value': setting.value,
                'description': setting.description
            })
        
        # إنشاء ملف مؤقت للتنزيل
        response = make_response(jsonify(backup_data))
        response.headers['Content-Disposition'] = 'attachment; filename=backup.json'
        response.headers['Content-Type'] = 'application/json'
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/get_users')
@login_required
def admin_get_users():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_type = request.args.get('user_type', '')
    
    query = User.query
    if user_type:
        query = query.filter_by(user_type=user_type)
    
    users = query.all()
    result = []
    
    for user in users:
        user_data = {
            'id': user.id,
            'name': user.name,
            'username': user.username,
            'user_type': user.user_type,
            'failed_login_attempts': user.failed_login_attempts,
            'is_locked': user.is_locked
        }
        
        # إضافة بيانات الطالب إذا كان المستخدم طالب
        if user.user_type == 'student':
            student = Student.query.filter_by(user_id=user.id).first()
            if student:
                user_data['student_id'] = student.student_id
                user_data['stage'] = student.stage
        
        result.append(user_data)
    
    return jsonify(result)

@app.route('/admin/api/courses', methods=['GET', 'POST'])
@login_required
def admin_get_courses():
    # فلترة حسب المرحلة والفصل إذا تم تحديدها
    stage = request.args.get('stage', type=int)
    semester = request.args.get('semester', type=int)
    search = request.args.get('search', '')
    
    query = Course.query
    
    if stage:
        query = query.filter_by(stage=stage)
    if semester:
        query = query.filter_by(semester=semester)
    if search:
        query = query.filter(Course.name.ilike(f'%{search}%'))
    
    courses = query.all()
    
    result = []
    for course in courses:
        result.append({
            'id': course.id,
            'name': course.name,
            'stage': course.stage,
            'semester': course.semester,
            'units': course.units
        })
    
    return jsonify({'courses': result})

@app.route('/admin/get_students')
@login_required
def admin_get_students():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # فلترة حسب المرحلة أو البحث
    stage = request.args.get('stage', type=int)
    search = request.args.get('search', '')
    
    query = Student.query.join(User, User.id == Student.user_id)
    
    if stage:
        query = query.filter(Student.stage == stage)
    if search:
        query = query.filter(User.name.ilike(f'%{search}%') | 
                             Student.student_id.ilike(f'%{search}%'))
    
    students = query.all()
    
    result = []
    for student in students:
        user = User.query.get(student.user_id)
        result.append({
            'id': student.id,
            'student_id': student.student_id,
            'name': user.name,
            'username': user.username,
            'stage': student.stage,
            'user_id': student.user_id,
            'failed_login_attempts': user.failed_login_attempts,
            'is_locked': user.is_locked
        })
    
    return jsonify(result)

@app.route('/admin/get_student_details')
@login_required
def admin_get_student_details():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    student_id = request.args.get('student_id', type=int)
    if not student_id:
        return jsonify({'error': 'يجب تحديد معرف الطالب'}), 400
    
    student = Student.query.get_or_404(student_id)
    user = User.query.get(student.user_id)
    
    result = {
        'id': student.id,
        'student_id': student.student_id,
        'name': user.name,
        'username': user.username,
        'stage': student.stage,
        'user_id': student.user_id,
        'failed_login_attempts': user.failed_login_attempts,
        'is_locked': user.is_locked
    }
    
    return jsonify(result)

@app.route('/admin/add_course', methods=['POST'])
@login_required
def admin_add_course():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        name = request.form.get('name')
        stage = int(request.form.get('stage'))
        semester = int(request.form.get('semester'))
        units = int(request.form.get('units'))
        
        # التحقق من وجود المقرر
        existing_course = Course.query.filter_by(name=name, stage=stage, semester=semester).first()
        if existing_course:
            return jsonify({'error': 'المقرر موجود بالفعل في هذه المرحلة والفصل'}), 400
        
        # إنشاء المقرر الجديد
        course = Course(
            name=name,
            stage=stage,
            semester=semester,
            units=units
        )
        db.session.add(course)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تمت إضافة المقرر بنجاح',
            'course_id': course.id
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء إضافة المقرر: {str(e)}'}), 500

@app.route('/admin/update_course', methods=['POST'])
@login_required
def admin_update_course():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        course_id = request.form.get('course_id')
        name = request.form.get('name')
        stage = int(request.form.get('stage'))
        semester = int(request.form.get('semester'))
        units = int(request.form.get('units'))
        
        course = Course.query.get_or_404(course_id)
        
        # التحقق من وجود مقرر آخر بنفس الاسم والمرحلة والفصل
        existing_course = Course.query.filter(
            Course.name == name,
            Course.stage == stage,
            Course.semester == semester,
            Course.id != course.id
        ).first()
        
        if existing_course:
            return jsonify({'error': 'يوجد مقرر آخر بنفس الاسم في هذه المرحلة والفصل'}), 400
        
        # تحديث بيانات المقرر
        course.name = name
        course.stage = stage
        course.semester = semester
        course.units = units
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث بيانات المقرر بنجاح'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء تحديث بيانات المقرر: {str(e)}'}), 500

@app.route('/admin/delete_course', methods=['POST'])
@login_required
def admin_delete_course():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        course_id = request.form.get('course_id')
        course = Course.query.get_or_404(course_id)
        
        # حذف الدرجات المرتبطة بالمقرر أولاً
        Grade.query.filter_by(course_id=course.id).delete()
        
        # حذف المقرر
        db.session.delete(course)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم حذف المقرر بنجاح'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء حذف المقرر: {str(e)}'}), 500

@app.route('/admin/get_user_details')
@login_required
def admin_get_user_details():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'يجب تحديد معرف المستخدم'}), 400
    
    user = User.query.get_or_404(user_id)
    
    result = {
        'id': user.id,
        'name': user.name,
        'username': user.username,
        'user_type': user.user_type,
        'failed_login_attempts': user.failed_login_attempts,
        'is_locked': user.is_locked
    }
    
    # إضافة بيانات الطالب إذا كان المستخدم طالب
    if user.user_type == 'student':
        student = Student.query.filter_by(user_id=user.id).first()
        if student:
            result['student_id'] = student.student_id
            result['stage'] = student.stage
    
    return jsonify(result)

@app.route('/admin/get_student_grades')
@login_required
def admin_get_student_grades_for_course():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    course_id = request.args.get('course_id', type=int)
    stage = request.args.get('stage', type=int)
    
    if not course_id:
        return jsonify({'error': 'يجب تحديد معرف المقرر'}), 400
    
    # جلب جميع طلاب المرحلة
    students_query = Student.query
    if stage:
        students_query = students_query.filter_by(stage=stage)
    
    students = students_query.all()
    
    result = []
    for student in students:
        user = User.query.get(student.user_id)
        grade = Grade.query.filter_by(student_id=student.id, course_id=course_id).first()
        
        student_data = {
            'student_id': student.id,
            'student_number': student.student_id,
            'student_name': user.name,
            'grade_id': grade.id if grade else None,
            'coursework': grade.coursework if grade else None,
            'final_exam': grade.final_exam if grade else None,
            'decision_marks': grade.decision_marks if grade else None,
            'has_failed_courses': grade.total < 50 if grade else False
        }
        
        result.append(student_data)
    
    return jsonify(result)

@app.route('/admin/save_grades', methods=['POST'])
@login_required
def admin_save_grades():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # استلام بيانات الدرجات
        data = request.json
        
        # تحديث الدرجات
        for grade_data in data['grades']:
            student_id = grade_data.get('student_id')
            course_id = grade_data.get('course_id')
            grade_id = grade_data.get('grade_id')
            coursework = grade_data.get('coursework')
            final_exam = grade_data.get('final_exam')
            
            # تحويل القيم إلى أرقام
            if coursework:
                try:
                    coursework = float(coursework)
                    if coursework > 30:
                        coursework = 30
                except:
                    coursework = None
            
            if final_exam:
                try:
                    final_exam = float(final_exam)
                    if final_exam > 70:
                        final_exam = 70
                except:
                    final_exam = None
            
            # إذا لم تكن هناك درجات، تخطي هذا الطالب
            if coursework is None and final_exam is None:
                continue
            
            # البحث عن الدرجة أو إنشاء واحدة جديدة
            grade = None
            if grade_id:
                grade = Grade.query.get(grade_id)
            
            if not grade:
                grade = Grade.query.filter_by(student_id=student_id, course_id=course_id).first()
            
            if not grade:
                grade = Grade(
                    student_id=student_id,
                    course_id=course_id,
                    coursework=coursework if coursework is not None else 0,
                    final_exam=final_exam if final_exam is not None else 0
                )
                db.session.add(grade)
            else:
                if coursework is not None:
                    grade.coursework = coursework
                if final_exam is not None:
                    grade.final_exam = final_exam
            
            # حساب المجموع
            grade.total = (grade.coursework or 0) + (grade.final_exam or 0)
            
            # تسجيل الدرجة المحدثة
            updated_grades.append({
                'student_id': student_id,
                'grade_id': grade.id
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'تم حفظ {len(updated_grades)} درجة بنجاح',
            'updatedGrades': updated_grades
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء حفظ الدرجات: {str(e)}'}), 500

@app.route('/admin/stats/students')
@login_required
def admin_stats_students():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    total_students = Student.query.count()
    
    # إحصاءات الطلاب حسب المرحلة
    students_by_stage = []
    for stage in range(1, 5):
        count = Student.query.filter_by(stage=stage).count()
        students_by_stage.append(count)
    
    return jsonify({
        'total_students': total_students,
        'students_by_stage': students_by_stage
    })

@app.route('/admin/stats/courses')
@login_required
def admin_stats_courses():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    total_courses = Course.query.count()
    
    # توزيع المقررات حسب المرحلة والفصل
    semester1_courses = []
    semester2_courses = []
    
    for stage in range(1, 5):
        sem1_count = Course.query.filter_by(stage=stage, semester=1).count()
        sem2_count = Course.query.filter_by(stage=stage, semester=2).count()
        semester1_courses.append(sem1_count)
        semester2_courses.append(sem2_count)
    
    return jsonify({
        'total_courses': total_courses,
        'semester1_courses': semester1_courses,
        'semester2_courses': semester2_courses
    })

@app.route('/admin/stats/success_rate_by_stage')
@login_required
def admin_stats_success_rate_by_stage():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    success_rates = []
    
    for stage in range(1, 5):
        # جلب جميع درجات طلاب هذه المرحلة
        students = Student.query.filter_by(stage=stage).all()
        total_grades = 0
        passed_grades = 0
        
        for student in students:
            grades = Grade.query.filter_by(student_id=student.id).all()
            for grade in grades:
                total_grades += 1
                if grade.total >= 50:  # اعتبار 50 هو الحد الأدنى للنجاح
                    passed_grades += 1
        
        # حساب نسبة النجاح
        success_rate = 0
        if total_grades > 0:
            success_rate = (passed_grades / total_grades) * 100
        
        success_rates.append(success_rate)
    
    return jsonify({
        'success_rates': success_rates
    })

@app.route('/admin/stats/grade_distribution')
@login_required
def admin_stats_grade_distribution():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    stage = request.args.get('stage', type=int)
    semester = request.args.get('semester', type=int)
    course_id = request.args.get('course_id', type=int)
    
    # تعيين المقررات التي سيتم حساب متوسط درجاتها
    courses = []
    
    if course_id:
        # جلب مقرر واحد فقط
        course = Course.query.get(course_id)
        if course:
            courses = [course]
    else:
        # جلب مقررات بناءً على المرحلة و/أو الفصل
        course_query = Course.query
        if stage:
            course_query = course_query.filter_by(stage=stage)
        if semester:
            course_query = course_query.filter_by(semester=semester)
        
        courses = course_query.all()
    
    if not courses:
        return jsonify({
            'labels': [],
            'averages': []
        })
    
    labels = []
    averages = []
    
    for course in courses:
        labels.append(course.name)
        
        # حساب متوسط الدرجات لهذا المقرر
        grades = Grade.query.filter_by(course_id=course.id).all()
        
        if not grades:
            averages.append(0)
            continue
        
        total_sum = sum(grade.total for grade in grades)
        average = total_sum / len(grades)
        averages.append(average)
    
    return jsonify({
        'labels': labels,
        'averages': averages
    })

@app.route('/admin/stats/top_bottom_students')
@login_required
def admin_stats_top_bottom_students():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # جلب جميع الطلاب وحساب متوسط درجاتهم
    students = Student.query.all()
    student_averages = []
    
    for student in students:
        grades = Grade.query.filter_by(student_id=student.id).all()
        
        if not grades:
            continue
        
        total_sum = sum(grade.total for grade in grades)
        average = total_sum / len(grades)
        
        user = User.query.get(student.user_id)
        
        student_averages.append({
            'id': student.id,
            'name': user.name,
            'student_id': student.student_id,
            'stage': student.stage,
            'average': average,
            'has_failed_courses': any(grade.total < 50 for grade in grades)
        })
    
    # ترتيب الطلاب حسب المتوسط
    student_averages.sort(key=lambda x: x['average'], reverse=True)
    
    # أخذ أعلى 10 وأدنى 10 طلاب
    top_students = student_averages[:10] if len(student_averages) >= 10 else student_averages
    bottom_students = student_averages[-10:] if len(student_averages) >= 10 else student_averages[::-1]
    
    return jsonify({
        'top_students': top_students,
        'bottom_students': bottom_students
    })

@app.route('/admin/stats/hardest_courses')
@login_required
def admin_stats_hardest_courses():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    courses = Course.query.all()
    course_success_rates = []
    
    for course in courses:
        grades = Grade.query.filter_by(course_id=course.id).all()
        
        if not grades:
            continue
        
        total_students = len(grades)
        passed_students = sum(1 for grade in grades if grade.total >= 50)
        
        success_rate = 0
        if total_students > 0:
            success_rate = (passed_students / total_students) * 100
        
        course_success_rates.append({
            'course_id': course.id,
            'course_name': course.name,
            'success_rate': success_rate,
            'stage': course.stage,
            'semester': course.semester
        })
    
    # ترتيب المقررات حسب نسبة النجاح (من الأقل إلى الأعلى)
    course_success_rates.sort(key=lambda x: x['success_rate'])
    
    # أخذ أصعب 10 مقررات
    hardest_courses = course_success_rates[:10] if len(course_success_rates) >= 10 else course_success_rates
    
    return jsonify({
        'course_names': [course['course_name'] for course in hardest_courses],
        'success_rates': [course['success_rate'] for course in hardest_courses]
    })

@app.route('/admin/export/students')
@login_required
def admin_export_students():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    format_type = request.args.get('format', 'csv')
    stage = request.args.get('stage', type=int)
    
    # جلب بيانات الطلاب
    query = Student.query.join(User, User.id == Student.user_id)
    
    if stage:
        query = query.filter(Student.stage == stage)
    
    students = query.all()
    
    # تجهيز البيانات
    student_data = []
    for student in students:
        user = User.query.get(student.user_id)
        student_data.append({
            'student_id': student.student_id,
            'name': user.name,
            'username': user.username,
            'stage': student.stage,
            'has_failed_courses': any(grade.total < 50 for grade in Grade.query.filter_by(student_id=student.id).all())
        })
    
    # تصدير البيانات حسب الصيغة المطلوبة
    if format_type == 'csv':
        # إنشاء ملف CSV
        output = io.StringIO()
        fieldnames = ['student_id', 'name', 'username', 'stage', 'has_failed_courses']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(student_data)
        
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=students.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response
    
    elif format_type == 'excel':
        # إنشاء ملف Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()
        
        # كتابة الرؤوس
        headers = ['رقم الطالب', 'الإسم', 'اسم المستخدم', 'المرحلة', 'راسب في أي مادة']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)
        
        # كتابة البيانات
        for row, student in enumerate(student_data, 1):
            worksheet.write(row, 0, student['student_id'])
            worksheet.write(row, 1, student['name'])
            worksheet.write(row, 2, student['username'])
            worksheet.write(row, 3, student['stage'])
            worksheet.write(row, 4, 'نعم' if student['has_failed_courses'] else 'لا')
        
        workbook.close()
        
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=students.xlsx'
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        return response
    
    elif format_type == 'pdf':
        # إنشاء ملف PDF
        pdf_buffer = io.BytesIO()
        pdf = canvas.Canvas(pdf_buffer, pagesize=letter)
        
        # إعداد الخط للغة العربية
        pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
        pdf.setFont('Arial', 12)
        
        # كتابة العنوان
        pdf.drawString(250, 750, "بيانات الطلاب")
        pdf.line(50, 735, 550, 735)
        
        # كتابة الرؤوس
        headers = ['رقم الطالب', 'الإسم', 'اسم المستخدم', 'المرحلة', 'راسب في أي مادة']
        x_positions = [50, 150, 300, 450, 550]
        y_position = 700
        
        for i, header in enumerate(headers):
            pdf.drawString(x_positions[i], y_position, header)
        
        pdf.line(50, y_position - 15, 550, y_position - 15)
        y_position -= 40
        
        # كتابة البيانات
        for student in student_data:
            pdf.drawString(x_positions[0], y_position, student['student_id'])
            pdf.drawString(x_positions[1], y_position, student['name'])
            pdf.drawString(x_positions[2], y_position, student['username'])
            pdf.drawString(x_positions[3], y_position, str(student['stage']))
            pdf.drawString(x_positions[4], y_position, 'نعم' if student['has_failed_courses'] else 'لا')
            
            y_position -= 25
            if y_position < 50:
                pdf.showPage()
                pdf.setFont('Arial', 12)
                y_position = 750
        
        pdf.save()
        
        pdf_buffer.seek(0)
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=students.pdf'
        response.headers['Content-Type'] = 'application/pdf'
        return response
    
    else:
        return jsonify({'error': 'صيغة التصدير غير مدعومة'}), 400

@app.route('/admin/import/students', methods=['POST'])
@login_required
def admin_import_students():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'students_file' not in request.files:
        return jsonify({'error': 'لم يتم تحديد ملف'}), 400
    
    file = request.files['students_file']
    if file.filename == '':
        return jsonify({'error': 'لم يتم اختيار ملف'}), 400
    
    # التحقق من نوع الملف
    if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({'error': 'نوع الملف غير مدعوم. يرجى استخدام CSV أو Excel'}), 400
    
    try:
        create_accounts = request.form.get('create_accounts') == 'on'
        imported_count = 0
        
        if file.filename.endswith('.csv'):
            # استيراد من CSV
            df = pd.read_csv(file, encoding='utf-8')
        else:
            # استيراد من Excel
            df = pd.read_excel(file)
        
        # التحقق من وجود الأعمدة المطلوبة
        required_columns = ['اسم الطالب', 'رقم الطالب', 'المرحلة']
        for column in required_columns:
            if column not in df.columns:
                return jsonify({'error': f'العمود "{column}" مفقود من الملف'}), 400
        
        # معالجة كل صف في الملف
        for _, row in df.iterrows():
            student_name = row['اسم الطالب']
            student_id = str(row['رقم الطالب'])
            stage = int(row['المرحلة'])
            
            # التحقق من وجود الطالب
            existing_student = Student.query.filter_by(student_id=student_id).first()
            
            if existing_student:
                # تحديث الطالب الموجود
                existing_student.stage = stage
                user = User.query.get(existing_student.user_id)
                user.name = student_name
            else:
                # إنشاء مستخدم جديد
                if create_accounts:
                    # إنشاء اسم مستخدم فريد
                    username = f"s{student_id}"
                    counter = 1
                    while User.query.filter_by(username=username).first():
                        username = f"s{student_id}_{counter}"
                        counter += 1
                    
                    # إنشاء مستخدم جديد
                    user = User(
                        name=student_name,
                        username=username,
                        user_type='student'
                    )
                    # تعيين كلمة مرور افتراضية هي رقم الطالب
                    user.set_password(student_id)
                    db.session.add(user)
                    db.session.flush()  # للحصول على معرف المستخدم
                    
                    # إنشاء سجل طالب جديد
                    student = Student(
                        user_id=user.id,
                        student_id=student_id,
                        stage=stage
                    )
                    db.session.add(student)
                    imported_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'تم استيراد {imported_count} طالب بنجاح',
            'imported_count': imported_count
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء استيراد بيانات الطلاب: {str(e)}'}), 500

# دالة لتهيئة الإعدادات
def initialize_settings():
    # تهيئة الجدول إذا لم يكن موجوداً
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table('settings'):
            Settings.__table__.create(db.engine)
            app.logger.info("تم إنشاء جدول الإعدادات")
        
        # إضافة الإعدادات الافتراضية إذا لم تكن موجودة
        default_settings = [
            {'key': 'current_academic_year', 'value': '2024-2025', 'description': 'العام الدراسي الحالي'},
            {'key': 'current_semester', 'value': '1', 'description': 'الفصل الدراسي الحالي'},
            {'key': 'min_pass_grade', 'value': '50', 'description': 'الحد الأدنى للنجاح'},
            {'key': 'max_decision_marks', 'value': '10', 'description': 'الحد الأقصى لدرجات القرار'}
        ]
        
        for setting in default_settings:
            existing_setting = Settings.query.filter_by(key=setting['key']).first()
            if not existing_setting:
                new_setting = Settings(
                    key=setting['key'],
                    value=setting['value'],
                    description=setting['description']
                )
                db.session.add(new_setting)
        
        db.session.commit()
        app.logger.info("تم تهيئة الإعدادات الافتراضية")
    except Exception as e:
        app.logger.error(f"خطأ في تهيئة الإعدادات: {str(e)}")
        db.session.rollback()

# استيراد درجات الطلاب
@app.route('/admin/import/courses', methods=['POST'])
@login_required
def admin_import_courses():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'courses_file' not in request.files:
        return jsonify({'error': 'لم يتم تحديد ملف'}), 400
    
    file = request.files['courses_file']
    if file.filename == '':
        return jsonify({'error': 'لم يتم اختيار ملف'}), 400
    
    # التحقق من نوع الملف
    if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({'error': 'نوع الملف غير مدعوم. يرجى استخدام CSV أو Excel'}), 400
    
    try:
        if file.filename.endswith('.csv'):
            # استيراد من CSV
            df = pd.read_csv(file, encoding='utf-8')
        else:
            # استيراد من Excel
            df = pd.read_excel(file)
        
        # التحقق من وجود الأعمدة المطلوبة
        required_columns = ['name', 'stage', 'semester', 'units']
        for column in required_columns:
            if column not in df.columns:
                return jsonify({'error': f'العمود "{column}" مفقود من الملف'}), 400
        
        # تحويل DataFrame إلى قائمة من القواميس
        data = df.to_dict('records')
        
        # استدعاء دالة استيراد المقررات
        result = import_courses(data)
        
        return jsonify({
            'success': True,
            'message': f'تم استيراد {result["success_count"]} مقرر بنجاح',
            'imported_count': result['success_count'],
            'errors': result.get('errors', [])
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء استيراد بيانات المقررات: {str(e)}'}), 500

# تصدير بيانات المقررات
@app.route('/admin/export/courses')
@login_required
def admin_export_courses():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    format_type = request.args.get('format', 'csv')
    
    # جلب بيانات المقررات
    courses = Course.query.all()
    
    # تحضير البيانات للتصدير
    data = []
    for course in courses:
        data.append({
            'id': course.id,
            'name': course.name,
            'stage': course.stage,
            'semester': course.semester,
            'units': course.units
        })
    
    if format_type == 'csv':
        # تصدير كملف CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys() if data else [])
        writer.writeheader()
        writer.writerows(data)
        
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=courses.csv'
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        return response
    
    elif format_type == 'excel':
        # تصدير كملف Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='Courses', index=False)
        
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=courses.xlsx'
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        return response
    
    elif format_type == 'pdf':
        # تصدير كملف PDF
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        p.setFont('Helvetica', 10)
        
        # تحضير البيانات للطباعة
        y_position = 750
        p.drawString(100, y_position, 'تقرير المقررات الدراسية')
        y_position -= 20
        
        # طباعة رؤوس الجدول
        headers = ['معرف المقرر', 'اسم المقرر', 'المرحلة', 'الفصل الدراسي', 'عدد الوحدات']
        x_positions = [450, 350, 250, 150, 50]
        
        for i, header in enumerate(headers):
            p.drawString(x_positions[i], y_position, header)
        
        y_position -= 15
        p.line(20, y_position, 550, y_position)
        y_position -= 15
        
        # طباعة بيانات المقررات
        for item in data:
            if y_position < 50:  # انتقال إلى صفحة جديدة عندما تكون الصفحة ممتلئة
                p.showPage()
                p.setFont('Helvetica', 10)
                y_position = 750
            
            p.drawString(450, y_position, str(item['id']))
            p.drawString(350, y_position, item['name'])
            p.drawString(250, y_position, str(item['stage']))
            p.drawString(150, y_position, str(item['semester']))
            p.drawString(50, y_position, str(item['units']))
            
            y_position -= 15
        
        p.save()
        buffer.seek(0)
        
        response = make_response(buffer.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=courses.pdf'
        response.headers['Content-Type'] = 'application/pdf'
        return response
    
    else:
        return jsonify({'error': 'صيغة التصدير غير مدعومة'}), 400

# استيراد درجات الطلاب
@app.route('/admin/import/grades', methods=['POST'])
@login_required
def admin_import_grades():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'grades_file' not in request.files:
        return jsonify({'error': 'لم يتم تحديد ملف'}), 400
    
    file = request.files['grades_file']
    if file.filename == '':
        return jsonify({'error': 'لم يتم اختيار ملف'}), 400
    
    # التحقق من نوع الملف
    if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({'error': 'نوع الملف غير مدعوم. يرجى استخدام CSV أو Excel'}), 400
    
    try:
        if file.filename.endswith('.csv'):
            # استيراد من CSV
            df = pd.read_csv(file, encoding='utf-8')
        else:
            # استيراد من Excel
            df = pd.read_excel(file)
        
        # التحقق من وجود الأعمدة المطلوبة
        required_columns = ['student_id', 'course_id', 'coursework', 'final_exam']
        for column in required_columns:
            if column not in df.columns:
                return jsonify({'error': f'العمود "{column}" مفقود من الملف'}), 400
        
        # تحويل DataFrame إلى قائمة من القواميس
        data = df.to_dict('records')
        
        # استدعاء دالة استيراد الدرجات
        result = import_grades(data)
        
        return jsonify({
            'success': True,
            'message': f'تم استيراد {result["success_count"]} درجة بنجاح',
            'imported_count': result['success_count'],
            'errors': result.get('errors', [])
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء استيراد بيانات الدرجات: {str(e)}'}), 500

# تصدير درجات الطلاب
@app.route('/admin/export/grades')
@login_required
def admin_export_grades():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    format_type = request.args.get('format', 'csv')
    stage = request.args.get('stage', type=int)
    course_id = request.args.get('course_id', type=int)
    
    # جلب بيانات الدرجات
    grades_query = Grade.query.join(Student, Student.id == Grade.student_id).join(Course, Course.id == Grade.course_id).join(User, User.id == Student.user_id)
    
    if stage:
        grades_query = grades_query.filter(Student.stage == stage)
    
    if course_id:
        grades_query = grades_query.filter(Grade.course_id == course_id)
    
    grades = grades_query.all()
    
    # تحضير البيانات للتصدير
    data = []
    for grade in grades:
        student = Student.query.get(grade.student_id)
        course = Course.query.get(grade.course_id)
        user = User.query.get(student.user_id)
        
        data.append({
            'student_id': student.student_id,
            'student_name': user.name,
            'course_id': course.id,
            'course_name': course.name,
            'stage': student.stage,
            'coursework': grade.coursework,
            'final_exam': grade.final_exam,
            'decision_marks': grade.decision_marks,
            'total': grade.total,
            'grade_status': grade.grade_status,
            'grade_evaluation': grade.grade_evaluation,
            'academic_year': grade.academic_year
        })
    
    if format_type == 'csv':
        # تصدير كملف CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys() if data else [])
        writer.writeheader()
        writer.writerows(data)
        
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=grades.csv'
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        return response
    
    elif format_type == 'excel':
        # تصدير كملف Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name='Grades', index=False)
        
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=grades.xlsx'
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        return response
    
    elif format_type == 'pdf':
        # تصدير كملف PDF
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        p.setFont('Helvetica', 10)
        
        # تحضير البيانات للطباعة
        y_position = 750
        p.drawString(100, y_position, 'تقرير درجات الطلاب')
        y_position -= 20
        
        # طباعة رؤوس الجدول
        headers = ['اسم الطالب', 'رقم الطالب', 'المقرر', 'أعمال الفصل', 'الامتحان النهائي', 'درجات القرار', 'المجموع', 'التقدير']
        x_positions = [450, 380, 300, 240, 170, 110, 70, 20]
        
        for i, header in enumerate(headers):
            p.drawString(x_positions[i], y_position, header)
        
        y_position -= 15
        p.line(20, y_position, 550, y_position)
        y_position -= 15
        
        # طباعة بيانات الطلاب
        for item in data:
            if y_position < 50:  # انتقال إلى صفحة جديدة عندما تكون الصفحة ممتلئة
                p.showPage()
                p.setFont('Helvetica', 10)
                y_position = 750
            
            p.drawString(450, y_position, item['student_name'])
            p.drawString(380, y_position, str(item['student_id']))
            p.drawString(300, y_position, item['course_name'])
            p.drawString(240, y_position, str(item['coursework']))
            p.drawString(170, y_position, str(item['final_exam']))
            p.drawString(110, y_position, str(item['decision_marks']))
            p.drawString(70, y_position, str(item['total']))
            p.drawString(20, y_position, item['grade_evaluation'])
            
            y_position -= 15
        
        p.save()
        buffer.seek(0)
        
        response = make_response(buffer.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=grades.pdf'
        response.headers['Content-Type'] = 'application/pdf'
        return response
    
    else:
        return jsonify({'error': 'صيغة التصدير غير مدعومة'}), 400

@app.route('/admin/reset_attempts/<int:user_id>', methods=['POST'])
@login_required
def admin_reset_user_attempts(user_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'المستخدم غير موجود'}), 404
    
    user.failed_login_attempts = 0
    user.is_locked = False
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'تم إعادة ضبط محاولات تسجيل الدخول للمستخدم {user.username}'
    })
    flash(f'تم إعادة تعيين محاولات تسجيل الدخول وإلغاء قفل حساب {user.username} بنجاح', 'success')
    return redirect(url_for('admin_users'))

# استيراد درجات الطلاب


# صفحة عرض درجات طالب محدد
@app.route('/admin/student_grades/<int:student_id>')
@login_required
def admin_student_grades(student_id):
    if current_user.user_type != 'admin':
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('login'))
    
    # التحقق من وجود الطالب
    student = Student.query.get(student_id)
    if not student:
        flash('الطالب غير موجود', 'danger')
        return redirect(url_for('admin_students'))
    
    # جلب بيانات المستخدم
    user = User.query.get(student.user_id)
    
    # جلب درجات الطالب
    grades = Grade.query.join(Course, Course.id == Grade.course_id)\
                    .filter(Grade.student_id == student_id)\
                    .order_by(Course.stage, Course.semester, Course.name).all()
    
    # جلب جميع المقررات مرتبة حسب المرحلة
    courses = Course.query.order_by(Course.stage, Course.semester, Course.name).all()
    
    # تنظيم المقررات حسب المرحلة لتسهيل العرض في القالب
    courses_by_stage = {}
    for stage in range(1, 5):
        courses_by_stage[stage] = [course for course in courses if course.stage == stage]
    
    return render_template('admin_student_grades.html', 
                          student=student, 
                          user=user, 
                          grades=grades, 
                          courses=courses, 
                          courses_by_stage=courses_by_stage,
                          active_page='students')

# إضافة درجة جديدة
@app.route('/admin/add_grade', methods=['POST'])
@login_required
def admin_add_grade():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'غير مصرح لك بالوصول إلى هذه الوظيفة'}), 403
    
    try:
        student_id = request.form.get('student_id', type=int)
        course_id = request.form.get('course_id', type=int)
        coursework = request.form.get('coursework', type=float)
        final_exam = request.form.get('final_exam', type=float)
        decision_marks = request.form.get('decision_marks', type=float, default=0)
        academic_year = request.form.get('academic_year')
        
        # التحقق من المدخلات
        if not all([student_id, course_id, coursework is not None, final_exam is not None, academic_year]):
            return jsonify({'error': 'جميع الحقول المطلوبة يجب تعبئتها'}), 400
        
        # التحقق من عدم وجود درجة سابقة لنفس الطالب والمقرر والسنة الدراسية
        existing_grade = Grade.query.filter_by(
            student_id=student_id,
            course_id=course_id,
            academic_year=academic_year
        ).first()
        
        if existing_grade:
            return jsonify({'error': 'توجد درجة مسجلة بالفعل لهذا الطالب في هذا المقرر للعام الدراسي المحدد'}), 400
        
        # حساب المجموع والحالة والتقدير
        total = coursework + final_exam + decision_marks
        grade_status = 'pass' if total >= 50 else 'fail'
        grade_evaluation = calculate_grade_evaluation(total)
        
        # إنشاء سجل درجة جديد
        grade = Grade(
            student_id=student_id,
            course_id=course_id,
            coursework=coursework,
            final_exam=final_exam,
            decision_marks=decision_marks,
            total=total,
            grade_status=grade_status,
            grade_evaluation=grade_evaluation,
            academic_year=academic_year
        )
        
        db.session.add(grade)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إضافة الدرجة بنجاح'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء إضافة الدرجة: {str(e)}'}), 500

# تحديث درجة
@app.route('/admin/update_grade', methods=['POST'])
@login_required
def admin_update_grade():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'غير مصرح لك بالوصول إلى هذه الوظيفة'}), 403
    
    try:
        grade_id = request.form.get('grade_id', type=int)
        student_id = request.form.get('student_id', type=int)
        course_id = request.form.get('course_id', type=int)
        coursework = request.form.get('coursework', type=float)
        final_exam = request.form.get('final_exam', type=float)
        decision_marks = request.form.get('decision_marks', type=float, default=0)
        academic_year = request.form.get('academic_year')
        
        # التحقق من المدخلات
        if not all([grade_id, student_id, course_id, coursework is not None, final_exam is not None, academic_year]):
            return jsonify({'error': 'جميع الحقول المطلوبة يجب تعبئتها'}), 400
        
        # التحقق من وجود الدرجة
        grade = Grade.query.get(grade_id)
        if not grade:
            return jsonify({'error': 'الدرجة غير موجودة'}), 404
        
        # التحقق من عدم وجود درجة أخرى لنفس الطالب والمقرر والسنة الدراسية
        existing_grade = Grade.query.filter(
            Grade.id != grade_id,
            Grade.student_id == student_id,
            Grade.course_id == course_id,
            Grade.academic_year == academic_year
        ).first()
        
        if existing_grade:
            return jsonify({'error': 'توجد درجة مسجلة بالفعل لهذا الطالب في هذا المقرر للعام الدراسي المحدد'}), 400
        
        # حساب المجموع والحالة والتقدير
        total = coursework + final_exam + decision_marks
        grade_status = 'pass' if total >= 50 else 'fail'
        grade_evaluation = calculate_grade_evaluation(total)
        
        # تحديث بيانات الدرجة
        grade.course_id = course_id
        grade.coursework = coursework
        grade.final_exam = final_exam
        grade.decision_marks = decision_marks
        grade.total = total
        grade.grade_status = grade_status
        grade.grade_evaluation = grade_evaluation
        grade.academic_year = academic_year
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث الدرجة بنجاح'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء تحديث الدرجة: {str(e)}'}), 500

# حذف درجة
@app.route('/admin/delete_grade', methods=['POST'])
@login_required
def admin_delete_grade():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'غير مصرح لك بالوصول إلى هذه الوظيفة'}), 403
    
    try:
        data = request.get_json()
        grade_id = data.get('grade_id')
        
        if not grade_id:
            return jsonify({'error': 'معرف الدرجة مطلوب'}), 400
        
        # التحقق من وجود الدرجة
        grade = Grade.query.get(grade_id)
        if not grade:
            return jsonify({'error': 'الدرجة غير موجودة'}), 404
        
        # حذف الدرجة
        db.session.delete(grade)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم حذف الدرجة بنجاح'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء حذف الدرجة: {str(e)}'}), 500

# نقطة دخول التطبيق
if __name__ == '__main__':
    # تحقق مما إذا كنا على Render
    if 'RENDER' in os.environ:
        # تشغيل التطبيق على Render بدون تكوين SSL (Render يتعامل مع SSL)
        port = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # توليد شهادة SSL للبيئة المحلية فقط
        ssl_context = 'adhoc'
        app.run(debug=True, ssl_context=ssl_context, host='0.0.0.0')
