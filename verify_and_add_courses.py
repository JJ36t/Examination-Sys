from app import app, Course, db

def verify_and_add_courses():
    # قائمة المقررات المطلوبة للمراحل والفصول الدراسية المختلفة
    required_courses = {
        # المرحلة الأولى، الفصل الأول
        (1, 1): [
            {'name': 'اساسيات برمجة', 'units': 8},
            {'name': 'مقدمة في تكنلوجيا المعلومات', 'units': 8},
            {'name': 'تصميم منطقي', 'units': 6},
            {'name': 'اقتصاد', 'units': 4},
        ],
        # المرحلة الأولى، الفصل الثاني
        (1, 2): [
            {'name': 'هياكل متقطعة', 'units': 6},
            {'name': 'تركيب الحاسوب', 'units': 6},
            {'name': 'حقوق الانسان', 'units': 2},
            {'name': 'ديمقراطية', 'units': 2},
        ],
        # المرحلة الثانية، الفصل الأول
        (2, 1): [
            {'name': 'برمجة كيانية', 'units': 8},
            {'name': 'طرق عددية', 'units': 6},
            {'name': 'معالجات دقيقة', 'units': 8},
            {'name': 'اللغة العربية', 'units': 2},
        ],
        # المرحلة الثانية، الفصل الثاني
        (2, 2): [
            {'name': 'نظرية احتسابية', 'units': 4},
            {'name': 'هياكل بيانات', 'units': 8},
            {'name': 'احصاء', 'units': 4},
            {'name': 'جافا', 'units': 6},
        ],
        # المرحلة الثالثة، الفصل الأول
        (3, 1): [
            {'name': 'بحث ويب', 'units': 4},
            {'name': 'برمجة مواقع', 'units': 6},
            {'name': 'رسم بالحاسوب', 'units': 8},
            {'name': 'قواعد بيانات', 'units': 8},
        ],
        # المرحلة الثالثة، الفصل الثاني
        (3, 2): [
            {'name': 'مترجمات', 'units': 6},
            {'name': 'بايثون', 'units': 6},
            {'name': 'ذكاء اصطناعي', 'units': 6},
            {'name': 'تشفير', 'units': 4},
        ],
        # المرحلة الرابعة، الفصل الأول
        (4, 1): [
            {'name': 'انترنيت الاشياء', 'units': 6},
            {'name': 'نظم تشغيل', 'units': 8},
            {'name': 'معالجة صور', 'units': 8},
            {'name': 'امنية حواسيب', 'units': 4},
        ],
        # المرحلة الرابعة، الفصل الثاني
        (4, 2): [
            {'name': 'حوسبة سحابية', 'units': 4},
            {'name': 'تمييز انماط', 'units': 4},
            {'name': 'شبكات', 'units': 8},
            {'name': 'تجارة الكترونية', 'units': 4},
        ],
    }

    with app.app_context():
        added_count = 0  # عداد للمقررات المضافة
        
        print("جاري التحقق من المقررات وإضافة المفقودة:")
        print("-" * 50)
        
        for (stage, semester), courses in required_courses.items():
            print(f"\nالمرحلة {stage} - الكورس {semester}:")
            print("-" * 30)
            
            for course_data in courses:
                course_name = course_data['name']
                # البحث عن المقرر في قاعدة البيانات
                course_exists = Course.query.filter_by(
                    name=course_name, 
                    stage=stage, 
                    semester=semester
                ).first()
                
                if course_exists:
                    print(f"- المقرر '{course_name}' موجود بالفعل")
                    
                    # تحديث وحدات المقرر إذا كانت مختلفة
                    if course_exists.units != course_data['units']:
                        course_exists.units = course_data['units']
                        db.session.commit()
                        print(f"  - تم تحديث وحدات المقرر إلى {course_data['units']}")
                else:
                    # إضافة المقرر الجديد
                    new_course = Course(
                        name=course_name,
                        stage=stage,
                        semester=semester,
                        units=course_data['units']
                    )
                    db.session.add(new_course)
                    added_count += 1
                    print(f"+ تمت إضافة المقرر '{course_name}' ({course_data['units']} وحدات)")
        
        db.session.commit()
        
        print("\n" + "=" * 50)
        if added_count > 0:
            print(f"تم إضافة {added_count} مقرر جديد إلى قاعدة البيانات")
        else:
            print("جميع المقررات موجودة بالفعل في قاعدة البيانات")

if __name__ == "__main__":
    verify_and_add_courses()
