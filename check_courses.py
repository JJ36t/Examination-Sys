from app import app, Course, db

def check_courses():
    with app.app_context():
        print("المقررات المخزنة في قاعدة البيانات:")
        print("-" * 50)
        
        for stage in range(1, 5):
            for semester in range(1, 3):
                courses = Course.query.filter_by(stage=stage, semester=semester).all()
                print(f"\nالمرحلة {stage} - الكورس {semester}:")
                print("-" * 30)
                if courses:
                    for course in courses:
                        print(f"- {course.name} ({course.units} وحدات)")
                else:
                    print("لا توجد مقررات")

if __name__ == "__main__":
    check_courses()
