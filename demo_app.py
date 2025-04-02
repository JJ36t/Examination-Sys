"""
ملف تطبيق بسيط للتحقق من صحة التكوين على منصة Render
"""

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return "مرحبًا بك في تطبيق نظام الامتحانات! التطبيق يعمل بنجاح."

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    import os
    
    if 'RENDER' in os.environ:
        port = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        app.run(debug=True, host='0.0.0.0')
