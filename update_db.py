import sqlite3

def update_database():
    try:
        # الاتصال بقاعدة البيانات
        conn = sqlite3.connect('instance/examination.db')
        cursor = conn.cursor()
        
        # إضافة الأعمدة الجديدة إلى جدول المستخدمين
        cursor.execute('ALTER TABLE user ADD COLUMN failed_login_attempts INTEGER DEFAULT 0')
        cursor.execute('ALTER TABLE user ADD COLUMN is_locked BOOLEAN DEFAULT 0')
        
        # حفظ التغييرات
        conn.commit()
        print('تم تحديث قاعدة البيانات بنجاح')
        
        # إغلاق الاتصال
        conn.close()
    except Exception as e:
        print(f"حدث خطأ أثناء تحديث قاعدة البيانات: {e}")

if __name__ == "__main__":
    update_database()
