"""
Ealin 私人資訊管理系統 — Flask 主程式。

Routes:
  /              → 入口頁面
  /places/...    → 我想去的（Blueprint）
  /bucket-list/  → 人生待完成項目清單（Blueprint）
  /stocks/       → 零股管理（placeholder）
  /set-lang      → 切換語言
  /pwd/...       → 密碼管理子系統（Blueprint）
"""

import os
import shutil
import zipfile
from datetime import datetime
from io import BytesIO

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for

import config
from blueprints.bucket_list.routes import bucket_list_bp
from blueprints.places.routes import places_bp
from blueprints.pwd.routes import pwd_bp
from blueprints.stocks.routes import stocks_bp
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
app.register_blueprint(bucket_list_bp)
app.register_blueprint(stocks_bp)


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





@app.route('/ideas/')
def ideas():
    return render_template('placeholder.html', module_key='module.ideas')


@app.route('/api/system/backup')
def system_backup():
    try:
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(config.DATA_DIR):
                rel_dir = os.path.relpath(root, config.DATA_DIR)
                if 'backups' in rel_dir.split(os.sep):
                    continue
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, config.DATA_DIR)
                    zipf.write(file_path, arcname)
        
        memory_file.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'PrivateInfoMgr_backup_{timestamp}.zip'
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/system/restore', methods=['POST'])
def system_restore():
    if 'backup_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['backup_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    try:
        file_bytes = file.read()
        
        # Verify ZIP and inspect contents
        with zipfile.ZipFile(BytesIO(file_bytes)) as zipf:
            namelist = zipf.namelist()
            
            # Validation: Must contain at least one known index file or a db file
            required_files = {'index.json', 'places_index.json', 'bucket_list_index.json', 'stocks.db'}
            has_db = any(name.endswith('.db') for name in namelist)
            has_index = any(name in required_files for name in namelist)
            
            if not (has_db or has_index):
                return jsonify({'error': _t('system.restore.invalid_zip')}), 400
                
            # Perform automatic safety backup
            backups_dir = os.path.join(config.DATA_DIR, 'backups')
            os.makedirs(backups_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            auto_backup_filename = f'backup_auto_before_restore_{timestamp}.zip'
            auto_backup_path = os.path.join(backups_dir, auto_backup_filename)
            
            # Zip current data (excluding backups directory)
            with zipfile.ZipFile(auto_backup_path, 'w', zipfile.ZIP_DEFLATED) as zip_backup:
                for root, dirs, files in os.walk(config.DATA_DIR):
                    rel_dir = os.path.relpath(root, config.DATA_DIR)
                    if 'backups' in rel_dir.split(os.sep):
                        continue
                    for f in files:
                        file_path = os.path.join(root, f)
                        arcname = os.path.relpath(file_path, config.DATA_DIR)
                        zip_backup.write(file_path, arcname)
            
            # Clear Flask session to reset database sessions
            session.clear()
            
            # Delete current database and index files (except backups folder and secret key)
            for item in os.listdir(config.DATA_DIR):
                item_path = os.path.join(config.DATA_DIR, item)
                if item == 'backups':
                    continue
                if item == '.secret_key':
                    continue
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            
            # Extract ZIP contents
            zipf.extractall(config.DATA_DIR)
            
        success_message = _t('system.restore.success', file=os.path.join('data', 'backups', auto_backup_filename))
        return jsonify({
            'success': True,
            'message': success_message
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
