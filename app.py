"""
Ealin 私人資訊管理系統 — Flask 主程式。

Routes:
  /              → 入口頁面
  /places/       → 我想去的（placeholder）
  /bucket-list/  → 人生待完成項目清單（placeholder）
  /pwd/...       → 密碼管理子系統（Blueprint）
"""

import os

from flask import Flask, render_template

import config
from blueprints.pwd.routes import pwd_bp

app = Flask(__name__,
            template_folder=os.path.join(config.BUNDLE_DIR, 'templates'),
            static_folder=os.path.join(config.BUNDLE_DIR, 'static'))
app.secret_key = config.SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

app.register_blueprint(pwd_bp)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/places/')
def places():
    return render_template('placeholder.html', title='我想去的')


@app.route('/bucket-list/')
def bucket_list():
    return render_template('placeholder.html', title='人生待完成項目清單')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
