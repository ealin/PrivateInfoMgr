"""
Ealin 私人資訊管理系統 — Flask 主程式。

Routes:
  /              → 入口頁面
  /places/...    → 我想去的（Blueprint）
  /bucket-list/  → 人生待完成項目清單（placeholder）
  /stocks/       → 零股管理（placeholder）
  /set-lang      → 切換語言
  /pwd/...       → 密碼管理子系統（Blueprint）
"""

import os

from flask import Flask, redirect, render_template, request, session, url_for

import config
from blueprints.places.routes import places_bp
from blueprints.pwd.routes import pwd_bp
from i18n import DEFAULT_LANG, SUPPORTED_LANGS, get_locale, lang_options
from i18n import load_translations
from i18n import t as _t

app = Flask(__name__,
            template_folder=os.path.join(config.BUNDLE_DIR, 'templates'),
            static_folder=os.path.join(config.BUNDLE_DIR, 'static'))
app.secret_key = config.SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

load_translations()
app.register_blueprint(pwd_bp)
app.register_blueprint(places_bp)


@app.context_processor
def inject_i18n():
    return {
        't':               _t,
        'current_lang':    get_locale(),
        'supported_langs': lang_options(),
    }


@app.route('/set-lang', methods=['POST'])
def set_lang():
    lang = request.form.get('lang', DEFAULT_LANG)
    if lang in SUPPORTED_LANGS:
        session['lang'] = lang
    next_url = request.form.get('next') or request.referrer or url_for('home')
    return redirect(next_url)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/bucket-list/')
def bucket_list():
    return render_template('placeholder.html', module_key='module.bucket_list')


@app.route('/stocks/')
def stocks():
    return render_template('placeholder.html', module_key='module.stocks')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
