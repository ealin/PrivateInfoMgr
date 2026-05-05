"""Password Manager Blueprint — all routes and in-memory session store."""

import os
import secrets
import threading
import uuid
from dataclasses import dataclass
from functools import wraps

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, session, url_for)

import config
from crypto import (decrypt_field, decrypt_master_key, encrypt_field,
                    encrypt_master_key, generate_master_key, hash_password,
                    verify_password)
from i18n import t
from models import (create_record, create_user, delete_record, get_all_records,
                    get_record, get_user, init_db, load_db_index,
                    save_db_index, update_record)

pwd_bp = Blueprint('pwd', __name__, url_prefix='/pwd')

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
                return jsonify({'error': t('pwd.api.not_logged_in')}), 401
            return redirect(url_for('pwd.index'))
        return f(*args, **kwargs)
    return decorated


# ── Pages ────────────────────────────────────────────────────────────────────

@pwd_bp.route('/')
def index():
    if _get_session():
        return redirect(url_for('pwd.dashboard'))
    databases = load_db_index()
    return render_template('pwd/select_db.html', databases=databases)


@pwd_bp.route('/create-db', methods=['POST'])
def create_db():
    display_name = request.form.get('display_name', '').strip()
    username     = request.form.get('username', '').strip()
    password1    = request.form.get('password1', '')
    password2    = request.form.get('password2', '')

    if not all([display_name, username, password1, password2]):
        flash(t('pwd.flash.fill_all'), 'error')
        return redirect(url_for('pwd.index'))
    if password1 == password2:
        flash(t('pwd.flash.pwd_same'), 'error')
        return redirect(url_for('pwd.index'))

    db_file = uuid.uuid4().hex + '.db'
    init_db(db_file)

    master_key       = generate_master_key()
    enc_master, salt = encrypt_master_key(master_key, password2)
    p1_hash          = hash_password(password1)
    p2_hash          = hash_password(password2)

    create_user(db_file, username, p1_hash, p2_hash, enc_master, salt)

    idx = load_db_index()
    idx.append({'display_name': display_name, 'file': db_file})
    save_db_index(idx)

    token = _new_session(master_key, db_file, username)
    session['token'] = token
    flash(t('pwd.flash.db_created', name=display_name), 'success')
    return redirect(url_for('pwd.dashboard'))


@pwd_bp.route('/login', methods=['POST'])
def login():
    db_file   = request.form.get('db_file', '')
    username  = request.form.get('username', '').strip()
    password1 = request.form.get('password1', '')
    password2 = request.form.get('password2', '')

    known_files = {d['file'] for d in load_db_index()}
    if db_file not in known_files:
        flash(t('pwd.flash.db_missing'), 'error')
        return redirect(url_for('pwd.index'))

    user = get_user(db_file, username)
    if not user:
        flash(t('pwd.flash.auth_error'), 'error')
        return redirect(url_for('pwd.index'))
    if not verify_password(user['password1_hash'], password1):
        flash(t('pwd.flash.auth_error'), 'error')
        return redirect(url_for('pwd.index'))
    if not verify_password(user['password2_hash'], password2):
        flash(t('pwd.flash.auth_error'), 'error')
        return redirect(url_for('pwd.index'))

    try:
        master_key = decrypt_master_key(
            user['encrypted_master_key'], password2, user['master_key_salt'])
    except Exception:
        flash(t('pwd.flash.auth_error'), 'error')
        return redirect(url_for('pwd.index'))

    token = _new_session(master_key, db_file, username)
    session['token'] = token
    return redirect(url_for('pwd.dashboard'))


@pwd_bp.route('/logout', methods=['POST'])
def logout():
    _drop_session()
    return redirect(url_for('pwd.index'))


@pwd_bp.route('/delete-db', methods=['POST'])
def delete_db():
    data      = request.get_json()
    db_file   = data.get('db_file', '')
    username  = data.get('username', '').strip()
    password1 = data.get('password1', '')
    password2 = data.get('password2', '')

    idx = load_db_index()
    known = {d['file'] for d in idx}
    if db_file not in known:
        return jsonify({'error': t('pwd.api.db_not_found')}), 404

    user = get_user(db_file, username)
    if not user:
        return jsonify({'error': t('pwd.api.auth_error')}), 403
    if not verify_password(user['password1_hash'], password1):
        return jsonify({'error': t('pwd.api.auth_error')}), 403
    if not verify_password(user['password2_hash'], password2):
        return jsonify({'error': t('pwd.api.auth_error')}), 403

    db_full_path = os.path.join(config.DATA_DIR, db_file)
    if os.path.exists(db_full_path):
        os.remove(db_full_path)

    new_idx = [d for d in idx if d['file'] != db_file]
    save_db_index(new_idx)

    return jsonify({'success': True})


@pwd_bp.route('/dashboard')
@require_auth
def dashboard():
    sess = _get_session()
    idx  = load_db_index()
    info = next((d for d in idx if d['file'] == sess.db_file), None)
    return render_template('pwd/dashboard.html',
                           display_name=info['display_name'] if info else '',
                           username=sess.username)


# ── API ──────────────────────────────────────────────────────────────────────

@pwd_bp.route('/api/records', methods=['GET'])
@require_auth
def api_list_records():
    sess   = _get_session()
    rows   = get_all_records(sess.db_file)
    result = []
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


@pwd_bp.route('/api/records', methods=['POST'])
@require_auth
def api_create_record():
    sess = _get_session()
    data = request.get_json()
    if not data:
        return jsonify({'error': t('pwd.api.invalid_data')}), 400
    if not data.get('name', '').strip():
        return jsonify({'error': t('pwd.api.name_required')}), 400

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


@pwd_bp.route('/api/records/<int:record_id>', methods=['GET'])
@require_auth
def api_get_record(record_id):
    sess   = _get_session()
    record = get_record(sess.db_file, record_id)
    if not record:
        return jsonify({'error': t('pwd.api.record_not_found')}), 404
    mk = sess.master_key
    return jsonify({
        'id':      record['id'],
        'name':    decrypt_field(record['enc_name'],    mk),
        'url':     decrypt_field(record['enc_url'],     mk),
        'account': decrypt_field(record['enc_account'], mk),
        'note1':   decrypt_field(record['enc_note1'],   mk),
        'note2':   decrypt_field(record['enc_note2'],   mk),
    })


@pwd_bp.route('/api/records/<int:record_id>', methods=['PUT'])
@require_auth
def api_update_record(record_id):
    sess   = _get_session()
    record = get_record(sess.db_file, record_id)
    if not record:
        return jsonify({'error': t('pwd.api.record_not_found')}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': t('pwd.api.invalid_data')}), 400
    if not data.get('name', '').strip():
        return jsonify({'error': t('pwd.api.name_required')}), 400

    mk = sess.master_key
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


@pwd_bp.route('/api/records/<int:record_id>', methods=['DELETE'])
@require_auth
def api_delete_record(record_id):
    sess   = _get_session()
    record = get_record(sess.db_file, record_id)
    if not record:
        return jsonify({'error': t('pwd.api.record_not_found')}), 404
    delete_record(sess.db_file, record_id)
    return jsonify({'success': True})


@pwd_bp.route('/api/records/<int:record_id>/reveal', methods=['POST'])
@require_auth
def api_reveal_password(record_id):
    sess = _get_session()
    data = request.get_json()
    if not data:
        return jsonify({'error': t('pwd.api.invalid_data')}), 400

    password2 = data.get('password2', '')
    user = get_user(sess.db_file, sess.username)
    if not user or not verify_password(user['password2_hash'], password2):
        return jsonify({'error': t('pwd.api.pwd2_wrong')}), 403

    record = get_record(sess.db_file, record_id)
    if not record:
        return jsonify({'error': t('pwd.api.record_not_found')}), 404

    password = decrypt_field(record['enc_password'], sess.master_key)
    return jsonify({'password': password})
