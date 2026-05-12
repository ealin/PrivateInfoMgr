/* Bucket List — frontend logic */

function $(id) { return document.getElementById(id); }

function show(el) { el.hidden = false; }
function hide(el) { el.hidden = true; }

function backdropClose(modal, closeFn) {
  let fromBackdrop = false;
  modal.addEventListener('mousedown', (e) => { fromBackdrop = e.target === modal; });
  modal.addEventListener('click', (e) => {
    if (e.target === modal && fromBackdrop) closeFn();
  });
}

async function api(method, url, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || 'Request failed');
  return json;
}

document.addEventListener('click', (e) => {
  const btn = e.target.closest('.toggle-pw');
  if (!btn) return;
  const input = document.getElementById(btn.dataset.target);
  if (!input) return;
  input.type = input.type === 'password' ? 'text' : 'password';
  btn.style.color = input.type === 'text' ? 'var(--accent)' : '';
});

document.querySelectorAll('.flash').forEach(el => {
  setTimeout(() => el.remove(), 4000);
});

const loginModal = $('loginModal');
const loginModalClose = $('loginModalClose');
const loginDbFile = $('loginDbFile');
const loginModalTitle = $('loginModalTitle');

if (loginModal) {
  document.querySelectorAll('.db-item').forEach(btn => {
    btn.addEventListener('click', () => {
      loginDbFile.value = btn.dataset.dbFile;
      loginModalTitle.textContent = btn.dataset.dbName + ' — ' + (window.T ? T.login_suffix : '');
      $('loginUsername').value = '';
      $('login_p1').value = '';
      $('login_p2').value = '';
      show(loginModal);
      setTimeout(() => $('loginUsername').focus(), 60);
    });
  });

  loginModalClose.addEventListener('click', () => hide(loginModal));
  backdropClose(loginModal, () => hide(loginModal));
}

const deleteDbModal = $('deleteDbModal');
const deleteDbError = $('deleteDbError');

if (deleteDbModal) {
  function openDeleteDb(dbFile, dbName) {
    $('deleteDbFile').value = dbFile;
    $('deleteDbName').textContent = dbName;
    $('deleteDbUsername').value = '';
    $('deleteDb_p1').value = '';
    $('deleteDb_p2').value = '';
    deleteDbError.hidden = true;
    show(deleteDbModal);
    setTimeout(() => $('deleteDbUsername').focus(), 60);
  }

  function closeDeleteDb() {
    hide(deleteDbModal);
  }

  document.querySelectorAll('.db-delete-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      openDeleteDb(btn.dataset.dbFile, btn.dataset.dbName);
    });
  });

  $('deleteDbModalClose').addEventListener('click', closeDeleteDb);
  $('deleteDbCancelBtn').addEventListener('click', closeDeleteDb);
  backdropClose(deleteDbModal, closeDeleteDb);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !deleteDbModal.hidden) closeDeleteDb();
  });

  $('deleteDbConfirmBtn').addEventListener('click', async () => {
    const btn = $('deleteDbConfirmBtn');
    const dbFile = $('deleteDbFile').value;
    const username = $('deleteDbUsername').value.trim();
    const p1 = $('deleteDb_p1').value;
    const p2 = $('deleteDb_p2').value;

    if (!username || !p1 || !p2) {
      deleteDbError.textContent = window.T ? T.fill_all : '';
      deleteDbError.hidden = false;
      return;
    }

    btn.disabled = true;
    deleteDbError.hidden = true;
    try {
      await api('POST', '/bucket-list/delete-db', {
        db_file: dbFile,
        username,
        password1: p1,
        password2: p2,
      });
      closeDeleteDb();
      location.reload();
    } catch (err) {
      deleteDbError.textContent = err.message;
      deleteDbError.hidden = false;
      $('deleteDb_p1').value = '';
      $('deleteDb_p2').value = '';
      $('deleteDbUsername').focus();
    } finally {
      btn.disabled = false;
    }
  });
}

const recordsTbody = $('recordsTbody');
if (recordsTbody) {
  let allRecords = [];

  async function loadRecords() {
    try {
      allRecords = await api('GET', '/bucket-list/api/records');
      renderRecords(allRecords);
    } catch (err) {
      recordsTbody.innerHTML =
        `<tr><td colspan="6" class="text-center text-muted">${T.load_failed}${err.message}</td></tr>`;
    }
  }

  function updateCount(total) {
    const recordCountEl = $('recordCount');
    if (!recordCountEl) return;
    const num = `<span style="color:var(--accent);font-weight:700;font-size:15px">${total}</span>`;
    recordCountEl.innerHTML = T.count_total.replace('{n}', num);
  }

  function renderRecords(records) {
    updateCount(records.length);
    if (records.length === 0) {
      recordsTbody.innerHTML =
        `<tr><td colspan="6" class="text-center text-muted">${T.no_records}</td></tr>`;
      return;
    }
    recordsTbody.innerHTML = records.map(r => `
      <tr data-id="${r.id}">
        <td>${esc(r.goal)}</td>
        <td>${r.wish_date ? esc(r.wish_date) : '<span class="cell-empty">-</span>'}</td>
        <td>${r.completed_date ? esc(r.completed_date) : '<span class="cell-empty">-</span>'}</td>
        <td class="cell-note">${r.description ? esc(r.description) : '<span class="cell-empty">-</span>'}</td>
        <td class="cell-url">${r.photo_url ? `<a href="${esc(r.photo_url)}" target="_blank" rel="noopener">${esc(r.photo_url)}</a>` : '<span class="cell-empty">-</span>'}</td>
        <td>
          <div class="td-actions">
            <button class="btn btn--ghost btn--sm" onclick="openEdit(${r.id})">${T.edit}</button>
            <button class="btn btn--ghost btn--sm" style="color:var(--danger)" onclick="openDelete(${r.id}, '${esc(r.goal)}')">${T.delete}</button>
          </div>
        </td>
      </tr>`).join('');
  }

  function esc(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  const recordModal = $('recordModal');
  const recordModalTitle = $('recordModalTitle');
  const recordForm = $('recordForm');

  function openCreate() {
    $('recordId').value = '';
    $('f_goal').value = '';
    $('f_wish_date').value = '';
    $('f_completed_date').value = '';
    $('f_description').value = '';
    $('f_photo_url').value = '';
    recordModalTitle.textContent = T.add_record_title;
    show(recordModal);
    setTimeout(() => $('f_goal').focus(), 60);
  }

  async function openEdit(id) {
    try {
      const r = await api('GET', `/bucket-list/api/records/${id}`);
      $('recordId').value = r.id;
      $('f_goal').value = r.goal;
      $('f_wish_date').value = r.wish_date;
      $('f_completed_date').value = r.completed_date;
      $('f_description').value = r.description;
      $('f_photo_url').value = r.photo_url;
      recordModalTitle.textContent = T.edit_record_title;
      show(recordModal);
      setTimeout(() => $('f_goal').focus(), 60);
    } catch (err) {
      alert(T.load_record_failed + err.message);
    }
  }

  window.openEdit = openEdit;

  $('newRecordBtn').addEventListener('click', openCreate);
  $('recordModalClose').addEventListener('click', () => hide(recordModal));
  $('recordModalCancel').addEventListener('click', () => hide(recordModal));
  backdropClose(recordModal, () => hide(recordModal));

  recordForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = $('recordId').value;
    const payload = {
      goal: $('f_goal').value.trim(),
      wish_date: $('f_wish_date').value,
      completed_date: $('f_completed_date').value,
      description: $('f_description').value.trim(),
      photo_url: $('f_photo_url').value.trim(),
    };
    if (!payload.goal) {
      alert(T.goal_required);
      return;
    }

    const btn = $('recordSubmitBtn');
    btn.disabled = true;
    try {
      if (id) {
        await api('PUT', `/bucket-list/api/records/${id}`, payload);
      } else {
        await api('POST', '/bucket-list/api/records', payload);
      }
      hide(recordModal);
      await loadRecords();
    } catch (err) {
      alert(T.save_failed + err.message);
    } finally {
      btn.disabled = false;
    }
  });

  const deleteModal = $('deleteModal');
  const deleteRecordName = $('deleteRecordName');
  let deleteId = null;

  function openDelete(id, name) {
    deleteId = id;
    deleteRecordName.textContent = name;
    show(deleteModal);
  }

  window.openDelete = openDelete;

  $('deleteModalClose').addEventListener('click', () => hide(deleteModal));
  $('deleteCancelBtn').addEventListener('click', () => hide(deleteModal));
  backdropClose(deleteModal, () => hide(deleteModal));

  $('deleteConfirmBtn').addEventListener('click', async () => {
    const btn = $('deleteConfirmBtn');
    btn.disabled = true;
    try {
      await api('DELETE', `/bucket-list/api/records/${deleteId}`);
      hide(deleteModal);
      await loadRecords();
    } catch (err) {
      alert(T.delete_failed + err.message);
    } finally {
      btn.disabled = false;
    }
  });

  loadRecords();
}
