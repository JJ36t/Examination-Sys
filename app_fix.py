if __name__ == '__main__':
    # تحقق مما إذا كنا على Render، إذا كان كذلك فلا تستخدم HTTPS
    if 'RENDER' not in os.environ:
        # توليد شهادة SSL للبيئة المحلية فقط
        ssl_context = 'adhoc'
        app.run(debug=True, ssl_context=ssl_context, host='0.0.0.0')
    else:
        # تشغيل التطبيق على Render بدون تكوين SSL (Render يتعامل مع SSL)
        port = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=port, debug=False)
