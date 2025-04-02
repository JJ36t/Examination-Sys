#!/usr/bin/env bash
# exit on error
set -o errexit

# بناء التطبيق
pip install -r requirements.txt

# إنشاء المجلدات الضرورية
mkdir -p instance
mkdir -p uploads

# تهيئة قاعدة البيانات - تخطي في حالة الخطأ
python restore_data.py || echo "تم تخطي استعادة البيانات بسبب خطأ"
