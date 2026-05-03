"""
Local Password Manager — Flask application.

Session strategy:
  - Flask's signed cookie stores only a random `token` string.
  - An in-memory dict maps token → SessionData (master_key + db_file + username).
  - The Master Key is NEVER written to disk; losing the process clears all sessions.
"""

import secrets
import threading
import uuid
from dataclasses import dataclass
from functools import wraps

from flask import (Flask, flash, jsonify, redirect, render_template,
                   request, session, url_for)

import config
from crypto import (decrypt_field, decrypt_master_key, encrypt_field,
                    encrypt_master_key, generate_master_key, hash_password,
                    verify_password)
from models import (create_record, create_user, delete_record, get_all_records,
                    get_record, get_user, init_db, load_db_index,
                    save_db_index, update_record)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ── In-memory session store ──────────────────────────────────────────────────

@dataclass
class SessionData:
    master_key: bytes
    db_file: str
    username: str


_sessions: dict[str, SessionData] = {}
_sessions_lock = threading.Lock()


def _new_session(master_key: bytes, db_file: str, username: str) -> str:
    token = secrets.token_hex(32)
    with _sessions_lock:
        _sessions[token] = SessionData(master_key=master_key,
                                       db_file=db_file,
                                       username=username)
    return token


def _get_session() -> SessionData | None:
    token = session.get('token')
    if not token:
        return None
    with _sessions_lock:
        return _sessions.get(token)


def _drop_session() -> None:
    token = session.pop('token', None)
    if token:
        with _sessions_lock:
            _sessions.pop(token, None)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if _get_session() is None:
            if request.is_json:
                return jsonify({'error': '未登入'}), 401
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


# ── Pages ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if _get_session():
        return redirect(url_for('dashboard'))
    databases = load_db_index()
    return render_template('select_db.html', databases=databases)


@app.route('/create-db', methods=['POST'])
def create_db():
    display_name = request.form.get('display_name', '').strip()
    username     = request.form.get('username', '').strip()
    password1    = request.form.get('password1', '')
    password2    = request.form.get('password2', '')

    if not all([display_name, username, password1, password2]):
        flash('請填寫所有欄位', 'error')
        return redirect(url_for('index'))
    if password1 == password2:
        flash('兩層密碼不能相同', 'error')
        return redirect(url_for('index'))

    db_file = uuid.uuid4().hex + '.db'
    init_db(db_file)

    master_key          = generate_master_key()
    enc_master, salt    = encrypt_master_key(master_key, password2)
    p1_hash             = hash_password(password1)
    p2_hash             = hash_password(password2)

    create_user(db_file, username, p1_hash, p2_hash, enc_master, salt)

    idx = load_db_index()
    idx.append({'display_name': display_name, 'file': db_file})
    save_db_index(idx)

    token = _new_session(master_key, db_file, username)
    session['token'] = token
    flash(f'資料庫「{display_name}」已建立', 'success')
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['POST'])
def login():
    db_file   = request.form.get('db_file', '')
    username  = request.form.get('username', '').strip()
    password1 = request.form.get('password1', '')
    password2 = request.form.get('password2', '')

    # Validate db_file is a known database (prevent path traversal)
    known_files = {d['file'] for d in load_db_index()}
    if db_file not in known_files:
        flash('資料庫不存在', 'error')
        return redirect(url_for('index'))

    error_msg = '帳號或密碼錯誤'

    user = get_user(db_file, username)
    if not user:
        flash(error_msg, 'error')
        return redirect(url_for('index'))

    if not verify_password(user['password1_hash'], password1):
        flash(error_msg, 'error')
        return redirect(url_for('index'))

    if not verify_password(user['password2_hash'], password2):
        flash(error_msg, 'error')
        return redirect(url_for('index'))

    try:
        master_key = decrypt_master_key(
            user['encrypted_master_key'], password2, user['master_key_salt'])
    except Exception:
        flash(error_msg, 'error')
        return redirect(url_for('index'))

    token = _new_session(master_key, db_file, username)
    session['token'] = token
    return redirect(url_for('dashboard'))


@app.route('/logout', methods=['POST'])
def logout():
    _drop_session()
    return redirect(url_for('index'))


@app.route('/delete-db', methods=['POST'])
def delete_db():
    data      = request.get_json()
    db_file   = data.get('db_file', '')
    username  = data.get('username', '').strip()
    password1 = data.get('password1', '')
    password2 = data.get('password2', '')

    idx = load_db_index()
    known = {d['file'] for d in idx}
    if db_file not in known:
        return jsonify({'error': '資料庫不存在'}), 404

    error_msg = '帳號或密碼錯誤'
    user = get_user(db_file, username)
    if not user:
        return jsonify({'error': error_msg}), 403
    if not verify_password(user['password1_hash'], password1):
        return jsonify({'error': error_msg}), 403
    if not verify_password(user['password2_hash'], password2):
        return jsonify({'error': error_msg}), 403

    import os
    db_full_path = os.path.join(config.DATA_DIR, db_file)
    if os.path.exists(db_full_path):
        os.remove(db_full_path)

    new_idx = [d for d in idx if d['file'] != db_file]
    save_db_index(new_idx)

    return jsonify({'success': True})


@app.route('/dashboard')
@require_auth
def dashboard():
    sess = _get_session()
    idx  = load_db_index()
    info = next((d for d in idx if d['file'] == sess.db_file), None)
    return render_template('dashboard.html',
                           display_name=info['display_name'] if info else '',
                           username=sess.username)


# ── API ──────────────────────────────────────────────────────────────────────

@app.route('/api/records', methods=['GET'])
@require_auth
def api_list_records():
    sess    = _get_session()
    rows    = get_all_records(sess.db_file)
    result  = []
    for r in rows:
        result.append({
            'id':         r['id'],
            'name':       decrypt_field(r['enc_name'],    sess.master_key),
            'url':        decrypt_field(r['enc_url'],     sess.master_key),
            'account':    decrypt_field(r['enc_account'], sess.master_key),
            'note1':      decrypt_field(r['enc_note1'],   sess.master_key),
            'note2':      decrypt_field(r['enc_note2'],   sess.master_key),
            'created_at': r['created_at'],
            'updated_at': r['updated_at'],
        })
    return jsonify(result)


@app.route('/api/records', methods=['POST'])
@require_auth
def api_create_record():
    sess = _get_session()
    data = request.get_json()
    if not data:
        return jsonify({'error': '無效資料'}), 400
    if not data.get('name', '').strip():
        return jsonify({'error': '名稱為必填'}), 400

    mk = sess.master_key
    record_id = create_record(
        sess.db_file,
        encrypt_field(data.get('name', ''),     mk),
        encrypt_field(data.get('url', ''),      mk),
        encrypt_field(data.get('account', ''),  mk),
        encrypt_field(data.get('password', ''), mk),
        encrypt_field(data.get('note1', ''),    mk),
        encrypt_field(data.get('note2', ''),    mk),
    )
    return jsonify({'id': record_id}), 201


@app.route('/api/records/<int:record_id>', methods=['GET'])
@require_auth
def api_get_record(record_id):
    sess   = _get_session()
    record = get_record(sess.db_file, record_id)
    if not record:
        return jsonify({'error': '記錄不存在'}), 404
    mk = sess.master_key
    return jsonify({
        'id':      record['id'],
        'name':    decrypt_field(record['enc_name'],    mk),
        'url':     decrypt_field(record['enc_url'],     mk),
        'account': decrypt_field(record['enc_account'], mk),
        'note1':   decrypt_field(record['enc_note1'],   mk),
        'note2':   decrypt_field(record['enc_note2'],   mk),
    })


@app.route('/api/records/<int:record_id>', methods=['PUT'])
@require_auth
def api_update_record(record_id):
    sess   = _get_session()
    record = get_record(sess.db_file, record_id)
    if not record:
        return jsonify({'error': '記錄不存在'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': '無效資料'}), 400
    if not data.get('name', '').strip():
        return jsonify({'error': '名稱為必填'}), 400

    mk = sess.master_key
    # Keep existing encrypted password if the field is left empty
    new_password = data.get('password', '')
    enc_password = (encrypt_field(new_password, mk)
                    if new_password
                    else record['enc_password'])

    update_record(
        sess.db_file, record_id,
        encrypt_field(data.get('name', ''),    mk),
        encrypt_field(data.get('url', ''),     mk),
        encrypt_field(data.get('account', ''), mk),
        enc_password,
        encrypt_field(data.get('note1', ''),   mk),
        encrypt_field(data.get('note2', ''),   mk),
    )
    return jsonify({'success': True})


@app.route('/api/records/<int:record_id>', methods=['DELETE'])
@require_auth
def api_delete_record(record_id):
    sess   = _get_session()
    record = get_record(sess.db_file, record_id)
    if not record:
        return jsonify({'error': '記錄不存在'}), 404
    delete_record(sess.db_file, record_id)
    return jsonify({'success': True})


@app.route('/api/records/<int:record_id>/reveal', methods=['POST'])
@require_auth
def api_reveal_password(record_id):
    sess = _get_session()
    data = request.get_json()
    if not data:
        return jsonify({'error': '無效資料'}), 400

    password2 = data.get('password2', '')
    user = get_user(sess.db_file, sess.username)
    if not user or not verify_password(user['password2_hash'], password2):
        return jsonify({'error': '第二層密碼錯誤'}), 403

    record = get_record(sess.db_file, record_id)
    if not record:
        return jsonify({'error': '記錄不存在'}), 404

    password = decrypt_field(record['enc_password'], sess.master_key)
    return jsonify({'password': password})


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
