#!/usr/bin/env bash
# exit on error
set -o errexit

# بناء التطبيق
pip install -r requirements.txt

# تهيئة قاعدة البيانات
python restore_data.py
