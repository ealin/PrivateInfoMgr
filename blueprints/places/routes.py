"""Places Blueprint — 我想去的 routes."""

import uuid
from urllib.parse import urlparse

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)

from blueprints.places.models import (create_place, get_all_places, get_place,
                                      init_places_db, load_places_index,
                                      save_place, save_places_index)
from i18n import t

places_bp = Blueprint('places', __name__, url_prefix='/places')


def _get_db_info(db_file: str) -> dict | None:
    return next((d for d in load_places_index() if d['file'] == db_file), None)


def _is_valid_url(url: str) -> bool:
    if not url:
        return False
    try:
        r = urlparse(url)
        return r.scheme in ('http', 'https') and bool(r.netloc)
    except Exception:
        return False


@places_bp.route('/')
def index():
    return render_template('places/select_db.html',
                           databases=load_places_index())


@places_bp.route('/create-db', methods=['POST'])
def create_db():
    display_name = request.form.get('display_name', '').strip()
    if not display_name:
        flash(t('places.flash.fill_all'), 'error')
        return redirect(url_for('places.index'))

    db_file = 'places_' + uuid.uuid4().hex + '.db'
    init_places_db(db_file)

    idx = load_places_index()
    idx.append({'display_name': display_name, 'file': db_file})
    save_places_index(idx)

    flash(t('places.flash.db_created', name=display_name), 'success')
    return redirect(url_for('places.list_places', db_file=db_file))


@places_bp.route('/<db_file>/')
def list_places(db_file):
    info = _get_db_info(db_file)
    if not info:
        flash(t('places.flash.db_missing'), 'error')
        return redirect(url_for('places.index'))
    return render_template('places/list.html',
                           db_file=db_file,
                           display_name=info['display_name'],
                           places=get_all_places(db_file))


@places_bp.route('/<db_file>/add', methods=['GET'])
def add_place_form(db_file):
    info = _get_db_info(db_file)
    if not info:
        return redirect(url_for('places.index'))
    return render_template('places/add.html',
                           db_file=db_file,
                           display_name=info['display_name'])


@places_bp.route('/<db_file>/add', methods=['POST'])
def add_place(db_file):
    info = _get_db_info(db_file)
    if not info:
        return redirect(url_for('places.index'))

    name     = request.form.get('name', '').strip()
    address  = request.form.get('address', '').strip()
    link1    = request.form.get('link1', '').strip()
    link2    = request.form.get('link2', '').strip()
    achieved = 1 if request.form.get('achieved') else 0
    note     = request.form.get('note', '').strip()

    if not name:
        flash(t('places.flash.name_required'), 'error')
        return redirect(url_for('places.add_place_form', db_file=db_file))

    create_place(db_file, name, address, link1, link2, achieved, note)
    return redirect(url_for('places.list_places', db_file=db_file))


@places_bp.route('/<db_file>/<int:place_id>/')
def place_detail(db_file, place_id):
    info = _get_db_info(db_file)
    if not info:
        return redirect(url_for('places.index'))
    place = get_place(db_file, place_id)
    if not place:
        flash(t('places.flash.not_found'), 'error')
        return redirect(url_for('places.list_places', db_file=db_file))
    return render_template('places/detail.html',
                           db_file=db_file,
                           display_name=info['display_name'],
                           place=place,
                           show_preview=_is_valid_url(place['link1']))


@places_bp.route('/<db_file>/<int:place_id>/update', methods=['POST'])
def update_place(db_file, place_id):
    if not _get_db_info(db_file):
        return jsonify({'error': 'not found'}), 404
    if not get_place(db_file, place_id):
        return jsonify({'error': t('places.flash.not_found')}), 404

    data = request.get_json()
    if data is None:
        return jsonify({'error': 'invalid request'}), 400

    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': t('places.flash.name_required')}), 400

    save_place(
        db_file, place_id,
        name,
        data.get('address', '').strip(),
        data.get('link1', '').strip(),
        data.get('link2', '').strip(),
        1 if data.get('achieved') else 0,
        data.get('note', '').strip(),
    )
    return jsonify({'success': True})
