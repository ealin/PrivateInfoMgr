"""Bucket List Blueprint — encrypted life goal records."""

import os
import secrets
import threading
import uuid
from dataclasses import dataclass
from functools import wraps

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, session, url_for)

import config
from blueprints.bucket_list.models import (create_record, create_user,
                                           delete_record, get_all_records,
                                           get_record, get_user,
                                           init_bucket_db, load_bucket_index,
                                           save_bucket_index, update_record)
from crypto import (decrypt_field, decrypt_master_key, encrypt_field,
                    encrypt_master_key, generate_master_key, hash_password,
                    verify_password)
from i18n import t

bucket_list_bp = Blueprint('bucket_list', __name__, url_prefix='/bucket-list')


@dataclass
class SessionData:
    master_key: bytes
    db_file: str
    username: str


_sessions: dict[str, SessionData] = {}
_sessions_lock = threading.Lock()


def _session_key() -> str:
    return 'bucket_list_token'


def _new_session(master_key: bytes, db_file: str, username: str) -> str:
    token = secrets.token_hex(32)
    with _sessions_lock:
        _sessions[token] = SessionData(master_key=master_key,
                                       db_file=db_file,
                                       username=username)
    return token


def _get_session() -> SessionData | None:
    token = session.get(_session_key())
    if not token:
        return None
    with _sessions_lock:
        return _sessions.get(token)


def _drop_session() -> None:
    token = session.pop(_session_key(), None)
    if token:
        with _sessions_lock:
            _sessions.pop(token, None)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if _get_session() is None:
            if request.is_json:
                return jsonify({'error': t('bucket.api.not_logged_in')}), 401
            return redirect(url_for('bucket_list.index'))
        return f(*args, **kwargs)
    return decorated


@bucket_list_bp.route('/')
def index():
    if _get_session():
        return redirect(url_for('bucket_list.dashboard'))
    return render_template('bucket_list/select_db.html',
                           databases=load_bucket_index())


@bucket_list_bp.route('/create-db', methods=['POST'])
def create_db():
    display_name = request.form.get('display_name', '').strip()
    username = request.form.get('username', '').strip()
    password1 = request.form.get('password1', '')
    password2 = request.form.get('password2', '')

    if not all([display_name, username, password1, password2]):
        flash(t('bucket.flash.fill_all'), 'error')
        return redirect(url_for('bucket_list.index'))
    if password1 == password2:
        flash(t('bucket.flash.pwd_same'), 'error')
        return redirect(url_for('bucket_list.index'))

    db_file = 'bucket_' + uuid.uuid4().hex + '.db'
    init_bucket_db(db_file)

    master_key = generate_master_key()
    enc_master, salt = encrypt_master_key(master_key, password2)
    create_user(db_file, username, hash_password(password1),
                hash_password(password2), enc_master, salt)

    idx = load_bucket_index()
    idx.append({'display_name': display_name, 'file': db_file})
    save_bucket_index(idx)

    session[_session_key()] = _new_session(master_key, db_file, username)
    flash(t('bucket.flash.db_created', name=display_name), 'success')
    return redirect(url_for('bucket_list.dashboard'))


@bucket_list_bp.route('/login', methods=['POST'])
def login():
    db_file = request.form.get('db_file', '')
    username = request.form.get('username', '').strip()
    password1 = request.form.get('password1', '')
    password2 = request.form.get('password2', '')

    known_files = {d['file'] for d in load_bucket_index()}
    if db_file not in known_files:
        flash(t('bucket.flash.db_missing'), 'error')
        return redirect(url_for('bucket_list.index'))

    user = get_user(db_file, username)
    if not user:
        flash(t('bucket.flash.auth_error'), 'error')
        return redirect(url_for('bucket_list.index'))
    if not verify_password(user['password1_hash'], password1):
        flash(t('bucket.flash.auth_error'), 'error')
        return redirect(url_for('bucket_list.index'))
    if not verify_password(user['password2_hash'], password2):
        flash(t('bucket.flash.auth_error'), 'error')
        return redirect(url_for('bucket_list.index'))

    try:
        master_key = decrypt_master_key(
            user['encrypted_master_key'], password2, user['master_key_salt'])
    except Exception:
        flash(t('bucket.flash.auth_error'), 'error')
        return redirect(url_for('bucket_list.index'))

    session[_session_key()] = _new_session(master_key, db_file, username)
    return redirect(url_for('bucket_list.dashboard'))


@bucket_list_bp.route('/logout', methods=['POST'])
def logout():
    _drop_session()
    return redirect(url_for('bucket_list.index'))


@bucket_list_bp.route('/delete-db', methods=['POST'])
def delete_db():
    data = request.get_json()
    db_file = data.get('db_file', '')
    username = data.get('username', '').strip()
    password1 = data.get('password1', '')
    password2 = data.get('password2', '')

    idx = load_bucket_index()
    known = {d['file'] for d in idx}
    if db_file not in known:
        return jsonify({'error': t('bucket.api.db_not_found')}), 404

    user = get_user(db_file, username)
    if not user:
        return jsonify({'error': t('bucket.api.auth_error')}), 403
    if not verify_password(user['password1_hash'], password1):
        return jsonify({'error': t('bucket.api.auth_error')}), 403
    if not verify_password(user['password2_hash'], password2):
        return jsonify({'error': t('bucket.api.auth_error')}), 403

    db_full_path = os.path.join(config.DATA_DIR, db_file)
    if os.path.exists(db_full_path):
        os.remove(db_full_path)

    save_bucket_index([d for d in idx if d['file'] != db_file])
    return jsonify({'success': True})


@bucket_list_bp.route('/dashboard')
@require_auth
def dashboard():
    sess = _get_session()
    info = next((d for d in load_bucket_index()
                 if d['file'] == sess.db_file), None)
    return render_template('bucket_list/dashboard.html',
                           display_name=info['display_name'] if info else '',
                           username=sess.username)


@bucket_list_bp.route('/api/records', methods=['GET'])
@require_auth
def api_list_records():
    sess = _get_session()
    result = []
    for r in get_all_records(sess.db_file):
        result.append({
            'id': r['id'],
            'goal': decrypt_field(r['enc_goal'], sess.master_key),
            'wish_date': decrypt_field(r['enc_wish_date'], sess.master_key),
            'completed_date': decrypt_field(r['enc_completed_date'], sess.master_key),
            'description': decrypt_field(r['enc_description'], sess.master_key),
            'photo_url': decrypt_field(r['enc_photo_url'], sess.master_key),
            'created_at': r['created_at'],
            'updated_at': r['updated_at'],
        })
    return jsonify(result)


@bucket_list_bp.route('/api/records', methods=['POST'])
@require_auth
def api_create_record():
    sess = _get_session()
    data = request.get_json()
    if not data:
        return jsonify({'error': t('bucket.api.invalid_data')}), 400
    if not data.get('goal', '').strip():
        return jsonify({'error': t('bucket.api.goal_required')}), 400

    mk = sess.master_key
    record_id = create_record(
        sess.db_file,
        encrypt_field(data.get('goal', ''), mk),
        encrypt_field(data.get('wish_date', ''), mk),
        encrypt_field(data.get('completed_date', ''), mk),
        encrypt_field(data.get('description', ''), mk),
        encrypt_field(data.get('photo_url', ''), mk),
    )
    return jsonify({'id': record_id}), 201


@bucket_list_bp.route('/api/records/<int:record_id>', methods=['GET'])
@require_auth
def api_get_record(record_id):
    sess = _get_session()
    record = get_record(sess.db_file, record_id)
    if not record:
        return jsonify({'error': t('bucket.api.record_not_found')}), 404
    mk = sess.master_key
    return jsonify({
        'id': record['id'],
        'goal': decrypt_field(record['enc_goal'], mk),
        'wish_date': decrypt_field(record['enc_wish_date'], mk),
        'completed_date': decrypt_field(record['enc_completed_date'], mk),
        'description': decrypt_field(record['enc_description'], mk),
        'photo_url': decrypt_field(record['enc_photo_url'], mk),
    })


@bucket_list_bp.route('/api/records/<int:record_id>', methods=['PUT'])
@require_auth
def api_update_record(record_id):
    sess = _get_session()
    if not get_record(sess.db_file, record_id):
        return jsonify({'error': t('bucket.api.record_not_found')}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': t('bucket.api.invalid_data')}), 400
    if not data.get('goal', '').strip():
        return jsonify({'error': t('bucket.api.goal_required')}), 400

    mk = sess.master_key
    update_record(
        sess.db_file, record_id,
        encrypt_field(data.get('goal', ''), mk),
        encrypt_field(data.get('wish_date', ''), mk),
        encrypt_field(data.get('completed_date', ''), mk),
        encrypt_field(data.get('description', ''), mk),
        encrypt_field(data.get('photo_url', ''), mk),
    )
    return jsonify({'success': True})


@bucket_list_bp.route('/api/records/<int:record_id>', methods=['DELETE'])
@require_auth
def api_delete_record(record_id):
    sess = _get_session()
    if not get_record(sess.db_file, record_id):
        return jsonify({'error': t('bucket.api.record_not_found')}), 404
    delete_record(sess.db_file, record_id)
    return jsonify({'success': True})
