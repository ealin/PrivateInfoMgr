/* Password Manager — frontend logic */

// ── Helpers ──────────────────────────────────────────────────────────────────

function $(id) { return document.getElementById(id); }

function show(el)   { el.hidden = false; }
function hide(el)   { el.hidden = true; }

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
      loginModalTitle.textContent = btn.dataset.dbName + ' — 登入';
      $('loginUsername').value = '';
      $('login_p1').value = '';
      $('login_p2').value = '';
      show(loginModal);
      setTimeout(() => $('loginUsername').focus(), 60);
    });
  });

  loginModalClose.addEventListener('click', () => hide(loginModal));
  loginModal.addEventListener('click', (e) => {
    if (e.target === loginModal) hide(loginModal);
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
      allRecords = await api('GET', '/api/records');
      renderRecords(allRecords);
    } catch (err) {
      recordsTbody.innerHTML =
        `<tr><td colspan="6" class="text-center text-muted">載入失敗：${err.message}</td></tr>`;
    }
  }

  function renderRecords(records) {
    if (records.length === 0) {
      recordsTbody.innerHTML =
        '<tr><td colspan="6" class="text-center text-muted">尚無記錄，請點擊「新增記錄」。</td></tr>';
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
            <button class="btn btn--ghost btn--sm" onclick="openReveal(${r.id}, '${esc(r.name)}')">查看密碼</button>
            <button class="btn btn--ghost btn--sm" onclick="openEdit(${r.id})">編輯</button>
            <button class="btn btn--ghost btn--sm" style="color:var(--danger)" onclick="openDelete(${r.id}, '${esc(r.name)}')">刪除</button>
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

  $('searchInput').addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase();
    if (!q) { renderRecords(allRecords); return; }
    renderRecords(allRecords.filter(r =>
      (r.name    || '').toLowerCase().includes(q) ||
      (r.url     || '').toLowerCase().includes(q) ||
      (r.account || '').toLowerCase().includes(q)
    ));
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
    recordModalTitle.textContent = '新增記錄';
    pwLabel.textContent = '密碼';
    $('f_password').placeholder = '';
    show(recordModal);
    setTimeout(() => $('f_name').focus(), 60);
  }

  async function openEdit(id) {
    try {
      const r = await api('GET', `/api/records/${id}`);
      $('recordId').value   = r.id;
      $('f_name').value     = r.name;
      $('f_url').value      = r.url;
      $('f_account').value  = r.account;
      $('f_password').value = '';
      $('f_note1').value    = r.note1;
      $('f_note2').value    = r.note2;
      recordModalTitle.textContent = '編輯記錄';
      pwLabel.textContent = '密碼（留空表示不修改）';
      $('f_password').placeholder = '留空表示不修改';
      show(recordModal);
      setTimeout(() => $('f_name').focus(), 60);
    } catch (err) {
      alert('載入記錄失敗：' + err.message);
    }
  }

  window.openEdit = openEdit;

  $('newRecordBtn').addEventListener('click', openCreate);
  $('recordModalClose').addEventListener('click', () => hide(recordModal));
  $('recordModalCancel').addEventListener('click', () => hide(recordModal));
  recordModal.addEventListener('click', (e) => { if (e.target === recordModal) hide(recordModal); });

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
    if (!payload.name) { alert('名稱為必填'); return; }
    const btn = $('recordSubmitBtn');
    btn.disabled = true;
    try {
      if (id) {
        await api('PUT', `/api/records/${id}`, payload);
      } else {
        await api('POST', '/api/records', payload);
      }
      hide(recordModal);
      await loadRecords();
    } catch (err) {
      alert('儲存失敗：' + err.message);
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
  revealModal.addEventListener('click', (e) => { if (e.target === revealModal) closeReveal(); });

  $('revealSubmitBtn').addEventListener('click', async () => {
    const p2 = revealPassword2.value;
    if (!p2) return;
    const btn = $('revealSubmitBtn');
    btn.disabled = true;
    hide(revealError);
    try {
      const data = await api('POST', `/api/records/${_revealId}/reveal`, { password2: p2 });
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
      $('copyPwBtn').textContent = '已複製';
      setTimeout(() => { $('copyPwBtn').textContent = '複製'; }, 1500);
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
  deleteModal.addEventListener('click', (e) => { if (e.target === deleteModal) hide(deleteModal); });

  $('deleteConfirmBtn').addEventListener('click', async () => {
    const btn = $('deleteConfirmBtn');
    btn.disabled = true;
    try {
      await api('DELETE', `/api/records/${_deleteId}`);
      hide(deleteModal);
      await loadRecords();
    } catch (err) {
      alert('刪除失敗：' + err.message);
    } finally {
      btn.disabled = false;
    }
  });

  // ── Init ───────────────────────────────────────────────────────────────────
  loadRecords();
}
