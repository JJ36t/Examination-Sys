from app import app, init_db

if __name__ == '__main__':
    with app.app_context():
        print("بدء استعادة بيانات المقررات والطلاب والدرجات...")
        init_db()
        print("تم استعادة البيانات بنجاح!")
