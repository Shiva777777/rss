/* =========================================================
   RSS Attendance System â€“ Frontend JavaScript
   ========================================================= */

const API = '';          // relative; nginx proxies /api â†’ backend
let   token  = localStorage.getItem('rss_token')  || null;
let   role   = localStorage.getItem('rss_role')   || null;
let   myUser = null;
let   dailyChart = null;
const adminUserFilters = { search: '', role: '', status: '' };
const adminAttendanceFilters = { from: '', to: '', query: '' };
let adminChartDays = 30;

// â”€â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const $ = id => document.getElementById(id);

function normalizeRole(value) {
  if (!value) return '';
  return String(value).split('.').pop().toLowerCase();
}

role = normalizeRole(role) || null;

function isAdmin() {
  return normalizeRole(myUser?.role || role) === 'admin';
}

async function api(path, method = 'GET', body = null, auth = true) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth && token) headers['Authorization'] = `Bearer ${token}`;
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw data;
  return data;
}

async function apiForm(path, formData) {
  const res = await fetch(API + path, {
    method: 'POST',
    body: formData,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw data;
  return data;
}

function showToast(msg, type = 'success') {
  const t = $('toast');
  t.textContent = msg;
  t.className = `toast show ${type}`;
  setTimeout(() => { t.className = 'toast'; }, 3500);
}

function setError(id, msg) { $(id).textContent = msg; }
function clearError(id)    { $(id).textContent = '';  }

// â”€â”€â”€ Loader â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
window.addEventListener('load', () => {
  setTimeout(() => { $('loader').classList.add('hidden'); initApp(); }, 600);
});

function initApp() {
  // Demo card date
  $('demoDate').textContent = new Date().toLocaleDateString('en-IN', { weekday:'long', day:'numeric', month:'long' });
  if (token) {
    loadUser();
  } else {
    showNavGuest();
    navigateTo('home');
  }
}

// â”€â”€â”€ Navigation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function navigateTo(page) {
  ['home','dashboard','admin'].forEach(p => {
    const el = $('page' + p.charAt(0).toUpperCase() + p.slice(1));
    if (el) el.classList.toggle('hidden', p !== page);
  });
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  const link = document.querySelector(`[data-page="${page}"]`);
  if (link) link.classList.add('active');
}

document.querySelectorAll('[data-page]').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    navigateTo(link.dataset.page);
    if (link.dataset.page === 'dashboard') loadDashboard();
    if (link.dataset.page === 'admin') loadAdmin();
  });
});

// â”€â”€â”€ Nav State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function showNavLoggedIn(user) {
  $('userBadge').style.display = 'flex';
  $('btnOpenLogin').style.display = 'none';
  $('userAvatar').textContent = user.name.charAt(0).toUpperCase();
  $('userNameNav').textContent = user.name.split(' ')[0];
  $('navDashboard').parentElement.style.display = '';
  $('navDashboard').style.display = '';
  if (isAdmin()) $('navAdmin').style.display = '';
  else $('navAdmin').style.display = 'none';
}
function showNavGuest() {
  $('userBadge').style.display = 'none';
  $('btnOpenLogin').style.display = '';
  $('navAdmin').style.display = 'none';
}

// â”€â”€â”€ Auth: Load user â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async function loadUser() {
  try {
    myUser = await api('/api/users/me');
    role = normalizeRole(myUser.role) || role;
    if (role) localStorage.setItem('rss_role', role);
    showNavLoggedIn(myUser);
    navigateTo('dashboard');
    loadDashboard();
  } catch {
    logout();
  }
}

// â”€â”€â”€ Modal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function openModal(tab = 'Login') {
  $('authModal').classList.add('open');
  switchTab(tab);
}
function closeModal() { $('authModal').classList.remove('open'); }

$('modalClose').onclick   = closeModal;
$('btnOpenLogin').onclick = () => openModal('Login');
$('btnGetStarted').onclick = () => {
  if (token) { navigateTo('dashboard'); loadDashboard(); }
  else openModal('Login');
};
$('btnLearnMore').onclick = () => document.getElementById('features').scrollIntoView({ behavior: 'smooth' });

$('authModal').addEventListener('click', e => {
  if (e.target === $('authModal')) closeModal();
});

// Tab switching
['Login','Register','Forgot'].forEach(t => {
  $('tab'+t).onclick = () => switchTab(t);
});
function switchTab(tab) {
  ['Login','Register','Forgot'].forEach(t => {
    $('form'+t).classList.toggle('hidden', t !== tab);
    $('tab'+t).classList.toggle('active', t === tab);
  });
}

// â”€â”€â”€ Register â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
$('btnRegister').onclick = async () => {
  clearError('registerError');
  $('registerSuccess').textContent = '';
  const btn = $('btnRegister');
  btn.disabled = true; btn.textContent = 'Creating...';

  try {
    await api('/api/auth/register', 'POST', {
      name:     $('regName').value.trim(),
      email:    $('regEmail').value.trim(),
      phone:    $('regPhone').value.trim() || null,
      state:    $('regState').value.trim() || null,
      city:     $('regCity').value.trim() || null,
      password: $('regPassword').value,
    }, false);
    $('registerSuccess').textContent = 'âœ… Account created! Please login.';
    setTimeout(() => switchTab('Login'), 1500);
  } catch (err) {
    setError('registerError', err.detail || 'Registration failed');
  } finally {
    btn.disabled = false; btn.textContent = 'Create Account';
  }
};

// â”€â”€â”€ Login â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
$('btnLogin').onclick = async () => {
  clearError('loginError');
  const btn = $('btnLogin');
  btn.disabled = true; btn.textContent = 'Signing in...';

  const fd = new FormData();
  fd.append('username', $('loginEmail').value.trim());
  fd.append('password', $('loginPassword').value);

  try {
    const data = await apiForm('/api/auth/login', fd);
    token = data.access_token;
    role  = normalizeRole(data.role);
    localStorage.setItem('rss_token', token);
    localStorage.setItem('rss_role',  role);
    closeModal();
    await loadUser();
    showToast('Welcome back! ðŸ™');
  } catch (err) {
    setError('loginError', err.detail || 'Login failed');
  } finally {
    btn.disabled = false; btn.textContent = 'Sign In';
  }
};

// â”€â”€â”€ Forgot Password â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
$('btnForgot').onclick = async () => {
  clearError('forgotError');
  $('forgotSuccess').textContent = '';
  const btn = $('btnForgot');
  btn.disabled = true; btn.textContent = 'Sending...';
  try {
    const data = await api('/api/auth/forgot-password', 'POST',
      { email: $('forgotEmail').value.trim() }, false);
    $('forgotSuccess').textContent = data.message;
    if (data.debug_token) {
      $('resetTokenSection').classList.remove('hidden');
      showToast('Debug token shown below. Remove in production!', 'error');
    }
  } catch (err) {
    setError('forgotError', err.detail || 'Request failed');
  } finally {
    btn.disabled = false; btn.textContent = 'Send Reset Link';
  }
};

$('btnResetPassword').onclick = async () => {
  clearError('resetError');
  $('resetSuccess').textContent = '';
  try {
    await api('/api/auth/reset-password', 'POST', {
      token: $('resetToken').value.trim(),
      new_password: $('resetNewPass').value,
    }, false);
    $('resetSuccess').textContent = 'âœ… Password reset! Please login.';
    setTimeout(() => switchTab('Login'), 1500);
  } catch (err) {
    setError('resetError', err.detail || 'Reset failed');
  }
};

// â”€â”€â”€ Logout â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function logout() {
  token = null; role = null; myUser = null;
  localStorage.removeItem('rss_token');
  localStorage.removeItem('rss_role');
  showNavGuest();
  navigateTo('home');
}
$('btnLogout').onclick = logout;

// â”€â”€â”€ Eye toggle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function toggleEye(inputId, el) {
  const inp = $(inputId);
  if (inp.type === 'password') { inp.type = 'text'; el.textContent = 'ðŸ™ˆ'; }
  else { inp.type = 'password'; el.textContent = 'ðŸ‘'; }
}

// â”€â”€â”€ Dashboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async function loadDashboard() {
  if (!myUser) return;
  updateGreeting();
  updateDashDateBadge();
  loadProfileUI();
  await loadAttendanceStatus();
  await loadAttendanceHistory();
}

function updateGreeting() {
  const h = new Date().getHours();
  const g = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
  $('dashGreeting').textContent = `${g}, ${myUser.name.split(' ')[0]}! ðŸ‘‹`;
}
function updateDashDateBadge() {
  $('dashDateBadge').textContent = new Date().toLocaleDateString('en-IN',
    { weekday:'long', day:'numeric', month:'long', year:'numeric' });
}

function loadProfileUI() {
  $('piName').textContent  = myUser.name  || 'â€”';
  $('piEmail').textContent = myUser.email || 'â€”';
  $('piPhone').textContent = myUser.phone || 'â€”';
  $('piState').textContent = myUser.state || 'â€”';
  $('piCity').textContent  = myUser.city  || 'â€”';
}

async function loadAttendanceStatus() {
  try {
    const today = await api('/api/attendance/today');
    const ring  = $('statusRing');
    const btn   = $('btnMarkAttendance');
    const hint  = $('attHint');
    const text  = $('btnAttText');
    const status = $('statusText');

    if (today) {
      ring.className = 'status-ring marked';
      status.textContent = 'Attendance Marked âœ“';
      btn.disabled = true;
      btn.classList.add('success');
      text.textContent = 'Jai Shree Ram âœ“';
      hint.textContent = `Marked at ${new Date(today.marked_at).toLocaleTimeString('en-IN')}`;
    } else {
      ring.className = 'status-ring unmarked';
      status.textContent = 'Not Marked Yet';
      btn.disabled = false;
      btn.classList.remove('success');
      text.textContent = 'Jai Shree Ram';
      hint.textContent = 'Click to mark your attendance for today';
    }
  } catch {
    $('attHint').textContent = 'Could not load status';
  }
}

$('btnMarkAttendance').addEventListener('click', async () => {
  const btn = $('btnMarkAttendance');
  btn.disabled = true;
  const origText = $('btnAttText').textContent;
  $('btnAttText').textContent = 'Marking...';
  try {
    await api('/api/attendance/mark', 'POST');
    showToast('ðŸ™ Jai Shree Ram! Attendance marked successfully!');
    await loadAttendanceStatus();
    await loadAttendanceHistory();
  } catch (err) {
    showToast(err.detail || 'Failed to mark attendance', 'error');
    btn.disabled = false;
    $('btnAttText').textContent = origText;
  }
});

async function loadAttendanceHistory() {
  try {
    const { records, total } = await api('/api/attendance/history?limit=50');
    $('statTotal').textContent = total;

    // Calculate streak & this month
    let streak = 0;
    let monthCount = 0;
    const thisMonth = new Date().getMonth();
    const thisYear  = new Date().getFullYear();

    const sorted = [...records].sort((a,b) => new Date(b.date) - new Date(a.date));
    const today = new Date(); today.setHours(0,0,0,0);

    let checkDate = new Date(today);
    for (const r of sorted) {
      const d = new Date(r.date); d.setHours(0,0,0,0);
      if (d.getTime() === checkDate.getTime()) {
        streak++;
        checkDate.setDate(checkDate.getDate() - 1);
      } else break;
    }

    records.forEach(r => {
      const d = new Date(r.date);
      if (d.getMonth() === thisMonth && d.getFullYear() === thisYear) monthCount++;
    });

    $('statStreak').textContent = streak;
    $('statMonth').textContent  = monthCount;
    $('attStreak').textContent  = streak > 0 ? `ðŸ”¥ ${streak} day streak` : '';

    // Render history list
    const list = $('historyList');
    if (records.length === 0) {
      list.innerHTML = '<div class="history-empty">No attendance records yet</div>';
      return;
    }
    list.innerHTML = records.slice(0, 30).map(r => `
      <div class="history-item">
        <div>
          <div class="history-date">${new Date(r.date).toLocaleDateString('en-IN', { weekday:'short', day:'numeric', month:'short', year:'numeric' })}</div>
          <div class="history-time">${new Date(r.marked_at).toLocaleTimeString('en-IN')}</div>
        </div>
        <span class="history-badge">Present âœ“</span>
      </div>
    `).join('');
  } catch {
    $('historyList').innerHTML = '<div class="history-empty">Could not load history</div>';
  }
}

// â”€â”€â”€ Profile Edit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
$('btnEditProfile').onclick = () => {
  $('profileInfo').classList.add('hidden');
  $('editProfileForm').classList.remove('hidden');
  $('epName').value  = myUser.name  || '';
  $('epPhone').value = myUser.phone || '';
  $('epState').value = myUser.state || '';
  $('epCity').value  = myUser.city  || '';
};
$('btnCancelEdit').onclick = () => {
  $('profileInfo').classList.remove('hidden');
  $('editProfileForm').classList.add('hidden');
};
$('btnSaveProfile').onclick = async () => {
  try {
    myUser = await api('/api/users/me', 'PUT', {
      name:  $('epName').value.trim()  || undefined,
      phone: $('epPhone').value.trim() || undefined,
      state: $('epState').value.trim() || undefined,
      city:  $('epCity').value.trim()  || undefined,
    });
    loadProfileUI();
    showNavLoggedIn(myUser);
    $('profileInfo').classList.remove('hidden');
    $('editProfileForm').classList.add('hidden');
    showToast('Profile updated! âœ…');
  } catch (err) {
    showToast(err.detail || 'Update failed', 'error');
  }
};

// â”€â”€â”€ Admin Panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async function loadAdmin() {
  if (!isAdmin()) {
    showToast('Admin access required', 'error');
    navigateTo('dashboard');
    return;
  }

  setupAdminControls();
  await loadAdminStats();
  await loadAdminUsers();
  await loadAdminAttendance();

  document.querySelectorAll('.admin-tab').forEach(tab => {
    if (tab.dataset.bound === '1') return;
    tab.dataset.bound = '1';
    tab.onclick = () => {
      document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const name = tab.dataset.atab;
      ['users', 'attendance', 'chart'].forEach(s => {
        $('atab-' + s).classList.toggle('hidden', s !== name);
      });
      if (name === 'chart') loadDailyChart();
    };
  });
}

async function loadAdminStats() {
  try {
    const stats = await api('/api/admin/stats');
    $('adminTotalUsers').textContent = stats.total_users;
    $('adminActiveUsers').textContent = stats.active_users;
    $('adminTodayAtt').textContent = stats.today_attendances;
    $('adminTotalAtt').textContent = stats.total_attendances;
  } catch {
    showToast('Failed to load admin stats', 'error');
  }
}

function setupAdminControls() {
  if (setupAdminControls.initialized) return;
  setupAdminControls.initialized = true;

  $('btnUserFilter').onclick = () => {
    adminUserFilters.search = $('userSearch').value.trim();
    adminUserFilters.role = $('userRoleFilter').value;
    adminUserFilters.status = $('userStatusFilter').value;
    loadAdminUsers();
  };

  $('btnUserClear').onclick = () => {
    $('userSearch').value = '';
    $('userRoleFilter').value = '';
    $('userStatusFilter').value = '';
    adminUserFilters.search = '';
    adminUserFilters.role = '';
    adminUserFilters.status = '';
    loadAdminUsers();
  };

  $('userSearch').addEventListener('keydown', e => {
    if (e.key === 'Enter') $('btnUserFilter').click();
  });

  $('btnFilter').onclick = () => {
    adminAttendanceFilters.from = $('filterDateFrom').value;
    adminAttendanceFilters.to = $('filterDateTo').value;
    adminAttendanceFilters.query = $('attUserQuery').value.trim();

    if (adminAttendanceFilters.from && adminAttendanceFilters.to && adminAttendanceFilters.from > adminAttendanceFilters.to) {
      showToast('From date cannot be after To date', 'error');
      return;
    }
    loadAdminAttendance();
  };

  $('btnClearFilter').onclick = () => {
    $('filterDateFrom').value = '';
    $('filterDateTo').value = '';
    $('attUserQuery').value = '';
    adminAttendanceFilters.from = '';
    adminAttendanceFilters.to = '';
    adminAttendanceFilters.query = '';
    loadAdminAttendance();
  };

  $('btnExportAttendance').onclick = exportAttendanceCsv;

  $('chartDays').onchange = () => {
    adminChartDays = parseInt($('chartDays').value || '30', 10);
  };
  $('btnRefreshChart').onclick = () => loadDailyChart();
}

async function loadAdminUsers() {
  try {
    const params = new URLSearchParams({ limit: '200' });
    if (adminUserFilters.search) params.set('search', adminUserFilters.search);
    if (adminUserFilters.role) params.set('role', adminUserFilters.role);
    if (adminUserFilters.status) params.set('is_active', adminUserFilters.status === 'active' ? 'true' : 'false');

    const users = await api(`/api/admin/users?${params.toString()}`);
    $('usersTableBody').innerHTML = users.map((u, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${u.name}</td>
        <td>${u.email}</td>
        <td>${u.phone || '—'}</td>
        <td>${u.state || '—'}</td>
        <td>${u.city || '—'}</td>
        <td>${normalizeRole(u.role) === 'admin' ? '<span class="badge-admin">Admin</span>' : '<span class="badge-user">User</span>'}</td>
        <td>${u.is_active ? '<span class="badge-active">Active</span>' : '<span class="badge-inactive">Inactive</span>'}</td>
        <td>${normalizeRole(u.role) === 'admin' ? '—' : (
          u.is_active
            ? `<button class="btn-deactivate" onclick="updateUserStatus(${u.id}, false)">Deactivate</button>`
            : `<button class="btn-reactivate" onclick="updateUserStatus(${u.id}, true)">Activate</button>`
        )}</td>
      </tr>
    `).join('') || '<tr><td colspan="9" class="loading-row">No users found</td></tr>';
  } catch {
    $('usersTableBody').innerHTML = '<tr><td colspan="9" class="loading-row">Failed to load</td></tr>';
  }
}

async function updateUserStatus(id, isActive) {
  const action = isActive ? 'activate' : 'deactivate';
  if (!confirm(`Are you sure you want to ${action} this user?`)) return;
  try {
    await api(`/api/admin/users/${id}/status?is_active=${isActive}`, 'PATCH');
    showToast(`User ${isActive ? 'activated' : 'deactivated'}`);
    await Promise.all([loadAdminUsers(), loadAdminStats()]);
  } catch (err) {
    showToast(err.detail || 'Failed', 'error');
  }
}

async function deactivateUser(id) {
  await updateUserStatus(id, false);
}

async function loadAdminAttendance() {
  try {
    const params = new URLSearchParams({ limit: '500' });
    if (adminAttendanceFilters.from) params.set('date_from', adminAttendanceFilters.from);
    if (adminAttendanceFilters.to) params.set('date_to', adminAttendanceFilters.to);
    if (adminAttendanceFilters.query) params.set('user_query', adminAttendanceFilters.query);

    const data = await api(`/api/admin/attendance?${params.toString()}`);
    $('attTableBody').innerHTML = data.records.map((r, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${r.user_name}</td>
        <td>${r.user_email}</td>
        <td>${new Date(r.date).toLocaleDateString('en-IN')}</td>
        <td>${new Date(r.marked_at).toLocaleString('en-IN')}</td>
        <td>${r.ip_address || '—'}</td>
      </tr>
    `).join('') || '<tr><td colspan="6" class="loading-row">No records</td></tr>';
  } catch {
    $('attTableBody').innerHTML = '<tr><td colspan="6" class="loading-row">Failed to load</td></tr>';
  }
}

async function exportAttendanceCsv() {
  try {
    const params = new URLSearchParams();
    if (adminAttendanceFilters.from) params.set('date_from', adminAttendanceFilters.from);
    if (adminAttendanceFilters.to) params.set('date_to', adminAttendanceFilters.to);
    if (adminAttendanceFilters.query) params.set('user_query', adminAttendanceFilters.query);
    const qs = params.toString();
    const url = `/api/admin/attendance/export${qs ? `?${qs}` : ''}`;

    const res = await fetch(API + url, {
      method: 'GET',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw err;
    }

    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = `attendance_export_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(downloadUrl);
    showToast('Attendance CSV downloaded');
  } catch (err) {
    showToast(err.detail || 'CSV export failed', 'error');
  }
}

async function loadDailyChart() {
  try {
    const days = parseInt(($('chartDays')?.value || adminChartDays || 30), 10);
    adminChartDays = days;
    const summary = await api(`/api/admin/attendance/daily-summary?days=${days}`);
    const labels = summary.map(r => r.date).reverse();
    const values = summary.map(r => r.count).reverse();

    if (dailyChart) dailyChart.destroy();
    const ctx = $('dailyChart').getContext('2d');
    dailyChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Daily Attendance',
          data: values,
          backgroundColor: 'rgba(255,140,0,0.6)',
          borderColor: 'rgba(255,140,0,1)',
          borderWidth: 1,
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { labels: { color: '#8b8fa8', font: { family: 'Outfit' } } },
        },
        scales: {
          x: { ticks: { color: '#8b8fa8' }, grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { ticks: { color: '#8b8fa8' }, grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true },
        },
      },
    });
  } catch {
    showToast('Failed to load chart', 'error');
  }
}
