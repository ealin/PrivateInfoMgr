/* Password Manager — frontend logic */

// ── Helpers ──────────────────────────────────────────────────────────────────

function $(id) { return document.getElementById(id); }

function show(el)   { el.hidden = false; }
function hide(el)   { el.hidden = true; }

function backdropClose(modal, closeFn) {
  let fromBackdrop = false;
  modal.addEventListener('mousedown', (e) => { fromBackdrop = e.target === modal; });
  modal.addEventListener('click',     (e) => { if (e.target === modal && fromBackdrop) closeFn(); });
}

async function api(method, url, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || '請求失敗');
  return json;
}

// ── Password visibility toggle ────────────────────────────────────────────────

document.addEventListener('click', (e) => {
  const btn = e.target.closest('.toggle-pw');
  if (!btn) return;
  const input = document.getElementById(btn.dataset.target);
  if (!input) return;
  input.type = input.type === 'password' ? 'text' : 'password';
  btn.style.color = input.type === 'text' ? 'var(--accent)' : '';
});

// ── Flash auto-dismiss ────────────────────────────────────────────────────────

document.querySelectorAll('.flash').forEach(el => {
  setTimeout(() => el.remove(), 4000);
});

// ══════════════════════════════════════════════════════════════════════════════
// SELECT DB PAGE
// ══════════════════════════════════════════════════════════════════════════════

const loginModal      = $('loginModal');
const loginModalClose = $('loginModalClose');
const loginDbFile     = $('loginDbFile');
const loginModalTitle = $('loginModalTitle');

if (loginModal) {
  // Open login modal when a DB card is clicked
  document.querySelectorAll('.db-item').forEach(btn => {
    btn.addEventListener('click', () => {
      loginDbFile.value     = btn.dataset.dbFile;
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

// ── Delete database modal ─────────────────────────────────────────────────────

const deleteDbModal      = $('deleteDbModal');
const deleteDbError      = $('deleteDbError');

if (deleteDbModal) {
  function openDeleteDb(dbFile, dbName) {
    $('deleteDbFile').value     = dbFile;
    $('deleteDbName').textContent = dbName;
    $('deleteDbUsername').value = '';
    $('deleteDb_p1').value      = '';
    $('deleteDb_p2').value      = '';
    deleteDbError.hidden        = true;
    show(deleteDbModal);
    setTimeout(() => $('deleteDbUsername').focus(), 60);
  }

  function closeDeleteDb() { hide(deleteDbModal); }

  document.querySelectorAll('.db-delete-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      openDeleteDb(btn.dataset.dbFile, btn.dataset.dbName);
    });
  });

  $('deleteDbModalClose').addEventListener('click', closeDeleteDb);
  $('deleteDbCancelBtn').addEventListener('click', closeDeleteDb);
  backdropClose(deleteDbModal, closeDeleteDb);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !deleteDbModal.hidden) closeDeleteDb(); });

  $('deleteDbConfirmBtn').addEventListener('click', async () => {
    const btn      = $('deleteDbConfirmBtn');
    const dbFile   = $('deleteDbFile').value;
    const username = $('deleteDbUsername').value.trim();
    const p1       = $('deleteDb_p1').value;
    const p2       = $('deleteDb_p2').value;

    if (!username || !p1 || !p2) {
      deleteDbError.textContent = window.T ? T.fill_all : '';
      deleteDbError.hidden = false;
      return;
    }

    btn.disabled = true;
    deleteDbError.hidden = true;
    try {
      await api('POST', '/pwd/delete-db', { db_file: dbFile, username, password1: p1, password2: p2 });
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

// ══════════════════════════════════════════════════════════════════════════════
// DASHBOARD PAGE
// ══════════════════════════════════════════════════════════════════════════════

const recordsTbody = $('recordsTbody');
if (!recordsTbody) { /* not on dashboard */ }
else {

  let allRecords = [];

  // ── Load records ───────────────────────────────────────────────────────────

  async function loadRecords() {
    try {
      allRecords = await api('GET', '/pwd/api/records');
      renderRecords(allRecords);
    } catch (err) {
      recordsTbody.innerHTML =
        `<tr><td colspan="6" class="text-center text-muted">${T.load_failed}${err.message}</td></tr>`;
    }
  }

  function renderRecords(records) {
    if (records.length === 0) {
      recordsTbody.innerHTML =
        `<tr><td colspan="6" class="text-center text-muted">${T.no_records}</td></tr>`;
      return;
    }
    recordsTbody.innerHTML = records.map(r => `
      <tr data-id="${r.id}">
        <td>${esc(r.name)}</td>
        <td class="cell-url">${r.url ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.url)}</a>` : '<span class="cell-empty">—</span>'}</td>
        <td>${r.account || '<span class="cell-empty">—</span>'}</td>
        <td class="cell-note">${r.note1 || '<span class="cell-empty">—</span>'}</td>
        <td class="cell-note">${r.note2 || '<span class="cell-empty">—</span>'}</td>
        <td>
          <div class="td-actions">
            <button class="btn btn--ghost btn--sm" onclick="openReveal(${r.id}, '${esc(r.name)}')">${T.view_pwd}</button>
            <button class="btn btn--ghost btn--sm" onclick="openEdit(${r.id})">${T.edit}</button>
            <button class="btn btn--ghost btn--sm" style="color:var(--danger)" onclick="openDelete(${r.id}, '${esc(r.name)}')">${T.delete}</button>
          </div>
        </td>
      </tr>`).join('');
  }

  function esc(str) {
    return String(str ?? '')
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }

  // ── Search ─────────────────────────────────────────────────────────────────

  const searchInput = $('searchInput');
  const searchClear = $('searchClear');

  searchInput.addEventListener('input', () => {
    const q = searchInput.value.trim().toLowerCase();
    searchClear.hidden = !q;
    renderRecords(q
      ? allRecords.filter(r => (r.name || '').toLowerCase().includes(q))
      : allRecords
    );
  });

  searchClear.addEventListener('click', () => {
    searchInput.value = '';
    searchClear.hidden = true;
    renderRecords(allRecords);
    searchInput.focus();
  });

  // ── Add / Edit modal ───────────────────────────────────────────────────────

  const recordModal      = $('recordModal');
  const recordModalTitle = $('recordModalTitle');
  const recordForm       = $('recordForm');
  const pwLabel          = $('pwLabel');

  function openCreate() {
    $('recordId').value   = '';
    $('f_name').value     = '';
    $('f_url').value      = '';
    $('f_account').value  = '';
    $('f_password').value = '';
    $('f_note1').value    = '';
    $('f_note2').value    = '';
    recordModalTitle.textContent = T.add_record_title;
    pwLabel.textContent = T.password_label;
    $('f_password').placeholder = '';
    show(recordModal);
    setTimeout(() => $('f_name').focus(), 60);
  }

  async function openEdit(id) {
    try {
      const r = await api('GET', `/pwd/api/records/${id}`);
      $('recordId').value   = r.id;
      $('f_name').value     = r.name;
      $('f_url').value      = r.url;
      $('f_account').value  = r.account;
      $('f_password').value = '';
      $('f_note1').value    = r.note1;
      $('f_note2').value    = r.note2;
      recordModalTitle.textContent = T.edit_record_title;
      pwLabel.textContent = T.password_edit_label;
      $('f_password').placeholder = T.password_edit_ph;
      show(recordModal);
      setTimeout(() => $('f_name').focus(), 60);
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
      name:     $('f_name').value.trim(),
      url:      $('f_url').value.trim(),
      account:  $('f_account').value.trim(),
      password: $('f_password').value,
      note1:    $('f_note1').value.trim(),
      note2:    $('f_note2').value.trim(),
    };
    if (!payload.name) { alert(T.name_required); return; }
    const btn = $('recordSubmitBtn');
    btn.disabled = true;
    try {
      if (id) {
        await api('PUT', `/pwd/api/records/${id}`, payload);
      } else {
        await api('POST', '/pwd/api/records', payload);
      }
      hide(recordModal);
      await loadRecords();
    } catch (err) {
      alert(T.save_failed + err.message);
    } finally {
      btn.disabled = false;
    }
  });

  // ── Reveal password modal ──────────────────────────────────────────────────

  const revealModal      = $('revealModal');
  const revealStep1      = $('revealStep1');
  const revealStep2      = $('revealStep2');
  const revealRecordName = $('revealRecordName');
  const revealPassword2  = $('revealPassword2');
  const revealError      = $('revealError');
  const revealResult     = $('revealResult');
  const revealCountdown  = $('revealCountdown');
  const countdownFill    = $('countdownFill');

  let _revealId        = null;
  let _countdownTimer  = null;

  function openReveal(id, name) {
    _revealId = id;
    revealRecordName.textContent = name;
    revealPassword2.value = '';
    hide(revealError);
    show(revealStep1);
    hide(revealStep2);
    clearCountdown();
    show(revealModal);
    setTimeout(() => revealPassword2.focus(), 60);
  }
  window.openReveal = openReveal;

  function closeReveal() {
    hide(revealModal);
    clearCountdown();
    revealResult.textContent = '';
    revealPassword2.value = '';
  }

  function clearCountdown() {
    if (_countdownTimer) { clearInterval(_countdownTimer); _countdownTimer = null; }
    countdownFill.style.width = '100%';
    revealCountdown.textContent = '20';
  }

  $('revealModalClose').addEventListener('click', closeReveal);
  backdropClose(revealModal, closeReveal);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !revealModal.hidden) closeReveal(); });

  $('revealSubmitBtn').addEventListener('click', async () => {
    const p2 = revealPassword2.value;
    if (!p2) return;
    const btn = $('revealSubmitBtn');
    btn.disabled = true;
    hide(revealError);
    try {
      const data = await api('POST', `/pwd/api/records/${_revealId}/reveal`, { password2: p2 });
      revealResult.textContent = data.password;
      hide(revealStep1);
      show(revealStep2);
      startCountdown();
    } catch (err) {
      revealError.textContent = err.message;
      show(revealError);
      revealPassword2.value = '';
      revealPassword2.focus();
    } finally {
      btn.disabled = false;
    }
  });

  revealPassword2.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') $('revealSubmitBtn').click();
  });

  function startCountdown() {
    let secs = 20;
    const total = 20;
    clearCountdown();
    _countdownTimer = setInterval(() => {
      secs--;
      revealCountdown.textContent = secs;
      countdownFill.style.width   = (secs / total * 100) + '%';
      if (secs <= 0) closeReveal();
    }, 1000);
  }

  $('copyPwBtn').addEventListener('click', () => {
    navigator.clipboard.writeText(revealResult.textContent).then(() => {
      $('copyPwBtn').textContent = T.copied;
      setTimeout(() => { $('copyPwBtn').textContent = T.copy; }, 1500);
    });
  });

  // ── Delete modal ───────────────────────────────────────────────────────────

  const deleteModal      = $('deleteModal');
  const deleteRecordName = $('deleteRecordName');
  let   _deleteId        = null;

  function openDelete(id, name) {
    _deleteId = id;
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
      await api('DELETE', `/pwd/api/records/${_deleteId}`);
      hide(deleteModal);
      await loadRecords();
    } catch (err) {
      alert(T.delete_failed + err.message);
    } finally {
      btn.disabled = false;
    }
  });

  // ── Init ───────────────────────────────────────────────────────────────────
  // readonly blocks browser autofill; remove it after the fill window passes
  setTimeout(() => {
    searchInput.removeAttribute('readonly');
    searchInput.value = '';
    searchClear.hidden = true;
  }, 200);
  loadRecords();
}
