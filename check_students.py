from app import app, db, Student

with app.app_context():
    print('أرقام الطلاب الحاليين:')
    students = Student.query.order_by(Student.student_id).all()
    for student in students:
        print(f"ID: {student.id}, رقم الطالب: {student.student_id}")
