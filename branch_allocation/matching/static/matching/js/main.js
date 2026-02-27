/* ── CollegeMatch Main JS ────────────────────────── */

// ── Toast notification ────────────────────────────
function showToast(msg, type = 'success') {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = `show ${type}`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.className = '', 3000);
}

// ── Login tab switcher ────────────────────────────
function switchMainTab(tab) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-switcher button').forEach(b => b.classList.remove('active'));
  const panel = document.getElementById('tab-' + tab);
  const btn = document.getElementById('btn-' + tab);
  if (panel) panel.classList.add('active');
  if (btn) btn.classList.add('active');
}

function switchSignupTab(tab) {
  document.querySelectorAll('.signup-tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.signup-tab-btn').forEach(b => b.classList.remove('active'));
  const panel = document.getElementById('stab-' + tab);
  const btn = document.getElementById('sbtn-' + tab);
  if (panel) panel.classList.add('active');
  if (btn) btn.classList.add('active');
}

// ── Drag-and-drop preference list ────────────────
let dragSrc = null;

function initDragList(listId) {
  const list = document.getElementById(listId);
  if (!list) return;

  list.addEventListener('dragstart', e => {
    const row = e.target.closest('.pref-row');
    if (!row) return;
    dragSrc = row;
    setTimeout(() => row.classList.add('dragging'), 0);
    e.dataTransfer.effectAllowed = 'move';
  });

  list.addEventListener('dragend', e => {
    const row = e.target.closest('.pref-row');
    if (row) row.classList.remove('dragging');
    list.querySelectorAll('.pref-row').forEach(r => r.classList.remove('drag-over'));
    dragSrc = null;
  });

  list.addEventListener('dragover', e => {
    e.preventDefault();
    const row = e.target.closest('.pref-row');
    if (!row || row === dragSrc) return;
    list.querySelectorAll('.pref-row').forEach(r => r.classList.remove('drag-over'));
    row.classList.add('drag-over');

    const kids = [...list.querySelectorAll('.pref-row')];
    const srcIdx = kids.indexOf(dragSrc);
    const tgtIdx = kids.indexOf(row);
    if (srcIdx < tgtIdx) list.insertBefore(dragSrc, row.nextSibling);
    else list.insertBefore(dragSrc, row);
    updateRanks(list);
  });

  list.addEventListener('drop', e => {
    e.preventDefault();
    list.querySelectorAll('.pref-row').forEach(r => r.classList.remove('drag-over'));
  });
}

function updateRanks(list) {
  list.querySelectorAll('.pref-row').forEach((row, i) => {
    const rankEl = row.querySelector('.pref-rank');
    if (rankEl) rankEl.textContent = `#${i + 1}`;
  });
}

// ── Save preferences via AJAX ─────────────────────
function savePreferences() {
  const list = document.getElementById('pref-list');
  if (!list) return;

  const rows = list.querySelectorAll('.pref-row');
  const orderedIds = [...rows].map(r => r.dataset.branchId);

  if (!orderedIds.length) {
    showToast('No preferences to save.', 'error');
    return;
  }

  const btn = document.getElementById('save-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }

  fetch(window.location.href, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify({ ordered_ids: orderedIds }),
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      showToast('✓ Preferences saved and submitted!', 'success');
      const pill = document.getElementById('pref-pill');
      if (pill) { pill.className = 'pill pill-green'; pill.textContent = '✓ Submitted'; }
    } else {
      showToast(data.error || 'Save failed.', 'error');
    }
  })
  .catch(() => showToast('Network error. Please try again.', 'error'))
  .finally(() => {
    if (btn) { btn.disabled = false; btn.textContent = '✓ Save & Submit'; }
  });
}

// ── CSRF cookie helper ────────────────────────────
function getCookie(name) {
  const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return v ? v.pop() : '';
}

// ── Auto-dismiss messages ─────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    document.querySelectorAll('.alert').forEach(el => {
      el.style.transition = 'opacity 0.5s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 500);
    });
  }, 4000);
});

// ── Confirm dangerous actions ─────────────────────
function confirmAction(msg) {
  return confirm(msg);
}
