/* =========================================================
   RSS Attendance System â€“ Frontend JavaScript
   ========================================================= */

const API = '';          // relative; nginx proxies /api â†’ backend
let   token  = localStorage.getItem('rss_token')  || null;
let   refreshToken = localStorage.getItem('rss_refresh_token') || null;
let   role   = localStorage.getItem('rss_role')   || null;
let   myUser = null;
let   dailyLineChart = null;
let   monthlyBarChart = null;
let   userStatusPieChart = null;
const adminUserFilters = { search: '', role: '', status: '' };
const adminAttendanceFilters = { from: '', to: '', query: '' };
const adminLeaveFilters = { status: '', query: '' };
let adminChartDays = 30;
let adminChartMonths = 12;

// â”€â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const $ = id => document.getElementById(id);

function normalizeRole(value) {
  if (!value) return '';
  return String(value).split('.').pop().toLowerCase();
}

role = normalizeRole(role) || null;

function currentRole() {
  return normalizeRole(myUser?.role || role);
}

function isSuperAdmin() {
  return currentRole() === 'super_admin';
}

function isAdmin() {
  return ['admin', 'super_admin'].includes(currentRole());
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatDate(value) {
  if (!value) return '—';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return String(value);
  return dt.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function leaveStatusBadge(statusValue) {
  const normalized = String(statusValue || '').toLowerCase();
  if (normalized === 'approved') return '<span class="badge-approved">Approved</span>';
  if (normalized === 'rejected') return '<span class="badge-rejected">Rejected</span>';
  return '<span class="badge-pending">Pending</span>';
}

async function api(path, method = 'GET', body = null, auth = true, retry = true) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth && token) headers['Authorization'] = `Bearer ${token}`;
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && auth && refreshToken && retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return api(path, method, body, auth, false);
    clearSession();
    throw { detail: 'Session expired. Please login again.' };
  }
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

async function refreshAccessToken() {
  if (!refreshToken) return false;
  try {
    const res = await fetch(API + '/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return false;
    token = data.access_token;
    refreshToken = data.refresh_token || refreshToken;
    role = normalizeRole(data.role || role);
    localStorage.setItem('rss_token', token);
    localStorage.setItem('rss_refresh_token', refreshToken);
    if (role) localStorage.setItem('rss_role', role);
    return true;
  } catch {
    return false;
  }
}

function clearSession() {
  token = null;
  refreshToken = null;
  role = null;
  myUser = null;
  localStorage.removeItem('rss_token');
  localStorage.removeItem('rss_refresh_token');
  localStorage.removeItem('rss_role');
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
    refreshToken = data.refresh_token || null;
    role  = normalizeRole(data.role);
    localStorage.setItem('rss_token', token);
    if (refreshToken) localStorage.setItem('rss_refresh_token', refreshToken);
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
async function logout() {
  try {
    if (token) {
      await api('/api/auth/logout', 'POST', { refresh_token: refreshToken }, true, false);
    }
  } catch {
    // Ignore logout API errors and clear local session anyway.
  }
  clearSession();
  showNavGuest();
  navigateTo('home');
}
$('btnLogout').onclick = () => { logout(); };

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
  setupLeaveControls();
  await loadAttendanceStatus();
  await loadAttendanceHistory();
  await loadMyLeaveRequests();
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

async function reverseGeocodeCity(latitude, longitude) {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}`,
      { headers: { Accept: 'application/json' } }
    );
    if (!res.ok) return null;
    const data = await res.json();
    const addr = data.address || {};
    return addr.city || addr.town || addr.village || addr.county || addr.state || null;
  } catch {
    return null;
  }
}

async function getAttendanceLocationPayload() {
  const fallback = { latitude: null, longitude: null, city: null };
  if (!navigator.geolocation) return fallback;

  try {
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        resolve,
        reject,
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    });

    const latitude = Number(position.coords.latitude.toFixed(6));
    const longitude = Number(position.coords.longitude.toFixed(6));
    const city = await reverseGeocodeCity(latitude, longitude);
    return { latitude, longitude, city };
  } catch {
    return fallback;
  }
}

$('btnMarkAttendance').addEventListener('click', async () => {
  const btn = $('btnMarkAttendance');
  btn.disabled = true;
  const origText = $('btnAttText').textContent;
  $('btnAttText').textContent = 'Marking...';
  try {
    const locationPayload = await getAttendanceLocationPayload();
    await api('/api/attendance/mark', 'POST', locationPayload);
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
function setupLeaveControls() {
  if (setupLeaveControls.initialized) return;
  setupLeaveControls.initialized = true;
  $('btnApplyLeave').onclick = submitLeaveRequest;
}

async function submitLeaveRequest() {
  clearError('leaveFormError');
  const startDate = $('leaveStartDate').value;
  const endDate = $('leaveEndDate').value;
  const reason = $('leaveReason').value.trim();

  if (!startDate || !endDate) {
    setError('leaveFormError', 'Start date and end date are required');
    return;
  }
  if (startDate > endDate) {
    setError('leaveFormError', 'Start date cannot be after end date');
    return;
  }
  if (!reason || reason.length < 5) {
    setError('leaveFormError', 'Reason must be at least 5 characters');
    return;
  }

  const btn = $('btnApplyLeave');
  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Submitting...';

  try {
    await api('/api/leaves/requests', 'POST', {
      start_date: startDate,
      end_date: endDate,
      reason,
    });
    $('leaveReason').value = '';
    $('leaveStartDate').value = '';
    $('leaveEndDate').value = '';
    showToast('Leave request submitted');
    await loadMyLeaveRequests();
    if (isAdmin()) await loadAdminLeaveRequests();
  } catch (err) {
    setError('leaveFormError', err.detail || 'Failed to submit leave request');
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

async function loadMyLeaveRequests() {
  const body = $('leaveHistoryTableBody');
  if (!body) return;

  try {
    const data = await api('/api/leaves/requests?limit=50');
    const records = data.records || [];
    if (records.length === 0) {
      body.innerHTML = '<tr><td colspan="6" class="loading-row">No leave requests found</td></tr>';
      return;
    }

    body.innerHTML = records.map((r, i) => {
      const isPending = String(r.status || '').toLowerCase() === 'pending';
      return `
        <tr>
          <td>${i + 1}</td>
          <td>${formatDate(r.start_date)}</td>
          <td>${formatDate(r.end_date)}</td>
          <td>${leaveStatusBadge(r.status)}</td>
          <td class="reason-cell">${escapeHtml(r.reason || '')}</td>
          <td>${isPending ? `<button class="btn-delete-leave" onclick="deleteLeaveRequest(${r.id})">Cancel</button>` : '—'}</td>
        </tr>
      `;
    }).join('');
  } catch {
    body.innerHTML = '<tr><td colspan="6" class="loading-row">Failed to load leave requests</td></tr>';
  }
}

async function deleteLeaveRequest(leaveId) {
  if (!confirm('Cancel this leave request?')) return;
  try {
    await api(`/api/leaves/requests/${leaveId}`, 'DELETE');
    showToast('Leave request cancelled');
    await loadMyLeaveRequests();
    if (isAdmin()) await loadAdminLeaveRequests();
  } catch (err) {
    showToast(err.detail || 'Failed to cancel leave request', 'error');
  }
}

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
  await loadAdminLeaveRequests();

  document.querySelectorAll('.admin-tab').forEach(tab => {
    if (tab.dataset.bound === '1') return;
    tab.dataset.bound = '1';
    tab.onclick = () => {
      document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const name = tab.dataset.atab;
      ['users', 'attendance', 'leaves', 'chart'].forEach(s => {
        $('atab-' + s).classList.toggle('hidden', s !== name);
      });
      if (name === 'leaves') loadAdminLeaveRequests();
      if (name === 'chart') loadAnalyticsCharts();
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

  $('btnLeaveFilter').onclick = () => {
    adminLeaveFilters.status = $('leaveStatusFilter').value;
    adminLeaveFilters.query = $('leaveUserQuery').value.trim();
    loadAdminLeaveRequests();
  };

  $('btnLeaveClear').onclick = () => {
    $('leaveStatusFilter').value = '';
    $('leaveUserQuery').value = '';
    adminLeaveFilters.status = '';
    adminLeaveFilters.query = '';
    loadAdminLeaveRequests();
  };

  $('leaveUserQuery').addEventListener('keydown', e => {
    if (e.key === 'Enter') $('btnLeaveFilter').click();
  });

  $('chartDays').onchange = () => {
    adminChartDays = parseInt($('chartDays').value || '30', 10);
  };
  $('chartMonths').onchange = () => {
    adminChartMonths = parseInt($('chartMonths').value || '12', 10);
  };
  $('btnRefreshChart').onclick = () => loadAnalyticsCharts();
}

function roleBadge(roleValue) {
  const normalized = normalizeRole(roleValue);
  if (normalized === 'super_admin') return '<span class="badge-admin">Super Admin</span>';
  if (normalized === 'admin') return '<span class="badge-admin">Admin</span>';
  if (normalized === 'moderator') return '<span class="badge-user">Moderator</span>';
  return '<span class="badge-user">User</span>';
}

function roleOptions(selectedRole) {
  const roles = [
    { value: 'super_admin', label: 'Super Admin' },
    { value: 'admin', label: 'Admin' },
    { value: 'moderator', label: 'Moderator' },
    { value: 'user', label: 'User' },
  ];
  return roles.map(r => `<option value="${r.value}" ${selectedRole === r.value ? 'selected' : ''}>${r.label}</option>`).join('');
}

function canManageStatus(targetUser) {
  const targetRole = normalizeRole(targetUser.role);
  const meRole = currentRole();
  if (targetUser.id === myUser?.id) return false;
  if (meRole === 'super_admin') return true;
  if (meRole === 'admin') return ['user', 'moderator'].includes(targetRole);
  return false;
}

function buildUserActionCell(user) {
  const actions = [];
  if (canManageStatus(user)) {
    actions.push(
      user.is_active
        ? `<button class="btn-deactivate" onclick="updateUserStatus(${user.id}, false)">Deactivate</button>`
        : `<button class="btn-reactivate" onclick="updateUserStatus(${user.id}, true)">Activate</button>`
    );
  }

  if (isSuperAdmin() && user.id !== myUser?.id) {
    const selectedRole = normalizeRole(user.role);
    actions.push(
      `<div style="display:flex;gap:6px;align-items:center;justify-content:center;flex-wrap:wrap;">` +
      `<select id="roleSel_${user.id}" class="select-input" style="min-width:120px;">${roleOptions(selectedRole)}</select>` +
      `<button class="btn-filter" style="padding:4px 10px;" onclick="updateUserRole(${user.id})">Set Role</button>` +
      `</div>`
    );
  }

  return actions.length ? actions.join('<br/>') : '—';
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
        <td>${roleBadge(u.role)}</td>
        <td>${u.is_active ? '<span class="badge-active">Active</span>' : '<span class="badge-inactive">Inactive</span>'}</td>
        <td>${buildUserActionCell(u)}</td>
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

async function updateUserRole(id) {
  const roleSelect = document.getElementById(`roleSel_${id}`);
  if (!roleSelect) return;
  const selectedRole = roleSelect.value;
  if (!selectedRole) return;

  if (!confirm(`Change user role to "${selectedRole}"?`)) return;

  try {
    await api(`/api/admin/users/${id}/role`, 'PATCH', { role: selectedRole });
    showToast('User role updated');
    await Promise.all([loadAdminUsers(), loadAdminStats()]);
  } catch (err) {
    showToast(err.detail || 'Failed to update role', 'error');
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
        <td>${r.marked_time ? String(r.marked_time).slice(0, 8) : '—'}</td>
        <td>${new Date(r.marked_at).toLocaleString('en-IN')}</td>
        <td>${r.ip_address || '—'}</td>
        <td>${r.city || '—'}</td>
        <td>${(r.latitude != null && r.longitude != null) ? `${Number(r.latitude).toFixed(5)}, ${Number(r.longitude).toFixed(5)}` : '—'}</td>
      </tr>
    `).join('') || '<tr><td colspan="9" class="loading-row">No records</td></tr>';
  } catch {
    $('attTableBody').innerHTML = '<tr><td colspan="9" class="loading-row">Failed to load</td></tr>';
  }
}

async function loadAdminLeaveRequests() {
  const body = $('adminLeavesTableBody');
  if (!body) return;

  try {
    const params = new URLSearchParams({ limit: '300' });
    if (adminLeaveFilters.status) params.set('status', adminLeaveFilters.status);
    if (adminLeaveFilters.query) params.set('user_query', adminLeaveFilters.query);

    const data = await api(`/api/admin/leaves/requests?${params.toString()}`);
    const records = data.records || [];
    if (records.length === 0) {
      body.innerHTML = '<tr><td colspan="8" class="loading-row">No leave requests found</td></tr>';
      return;
    }

    body.innerHTML = records.map((r, i) => {
      const isPending = String(r.status || '').toLowerCase() === 'pending';
      const actionCell = isPending
        ? (
          '<div class="admin-leave-actions">' +
          `<button class="btn-approve" onclick="reviewLeaveRequest(${r.id}, 'approved')">Approve</button>` +
          `<button class="btn-reject" onclick="reviewLeaveRequest(${r.id}, 'rejected')">Reject</button>` +
          '</div>'
        )
        : '—';

      return `
        <tr>
          <td>${i + 1}</td>
          <td>${escapeHtml(r.user_name || '')}</td>
          <td>${escapeHtml(r.user_email || '')}</td>
          <td>${formatDate(r.start_date)}</td>
          <td>${formatDate(r.end_date)}</td>
          <td>${leaveStatusBadge(r.status)}</td>
          <td class="reason-cell">${escapeHtml(r.reason || '')}</td>
          <td>${actionCell}</td>
        </tr>
      `;
    }).join('');
  } catch {
    body.innerHTML = '<tr><td colspan="8" class="loading-row">Failed to load leave requests</td></tr>';
  }
}

async function reviewLeaveRequest(leaveId, statusValue) {
  if (!['approved', 'rejected'].includes(statusValue)) return;
  const actionText = statusValue === 'approved' ? 'approve' : 'reject';
  if (!confirm(`Are you sure you want to ${actionText} this leave request?`)) return;

  try {
    await api(`/api/admin/leaves/requests/${leaveId}/review`, 'PATCH', { status: statusValue });
    showToast(`Leave request ${statusValue}`);
    await loadAdminLeaveRequests();
    await loadMyLeaveRequests();
  } catch (err) {
    showToast(err.detail || 'Failed to review leave request', 'error');
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

async function loadAnalyticsCharts() {
  try {
    const days = parseInt(($('chartDays')?.value || adminChartDays || 30), 10);
    const months = parseInt(($('chartMonths')?.value || adminChartMonths || 12), 10);
    adminChartDays = days;
    adminChartMonths = months;

    const data = await api(`/api/admin/analytics/overview?days=${days}&months=${months}`);
    renderDailyLineChart(data.daily_attendance || []);
    renderMonthlyBarChart(data.monthly_attendance || []);
    renderUserActivityPieChart(data.user_activity || { active_users: 0, inactive_users: 0 });
    renderTrendStats(data.attendance_trend || null);
  } catch (err) {
    showToast(err.detail || 'Failed to load analytics dashboard', 'error');
  }
}

function renderTrendStats(trend) {
  if (!trend) return;
  $('trendCurrentTotal').textContent = trend.current_period_total ?? 0;
  $('trendPreviousTotal').textContent = trend.previous_period_total ?? 0;
  const growth = Number(trend.growth_percentage || 0);
  const growthPrefix = growth > 0 ? '+' : '';
  $('trendGrowth').textContent = `${growthPrefix}${growth.toFixed(2)}% (${trend.trend || 'flat'})`;
  $('trendAvgPerDay').textContent = String(trend.average_per_day ?? 0);
}

function renderDailyLineChart(points) {
  const labels = points.map(p => {
    const d = new Date(p.date);
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  });
  const values = points.map(p => p.count);

  if (dailyLineChart) dailyLineChart.destroy();
  dailyLineChart = new Chart($('dailyLineChart').getContext('2d'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Attendance per day',
          data: values,
          borderColor: 'rgba(255,140,0,1)',
          backgroundColor: 'rgba(255,140,0,0.2)',
          fill: true,
          tension: 0.3,
          pointRadius: 2,
          pointHoverRadius: 4,
        },
      ],
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
}

function renderMonthlyBarChart(points) {
  const labels = points.map(p => p.month);
  const attendanceValues = points.map(p => p.attendance_count);

  if (monthlyBarChart) monthlyBarChart.destroy();
  monthlyBarChart = new Chart($('monthlyBarChart').getContext('2d'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Monthly attendance',
          data: attendanceValues,
          backgroundColor: 'rgba(61,142,240,0.55)',
          borderColor: 'rgba(61,142,240,1)',
          borderWidth: 1,
          borderRadius: 6,
        },
      ],
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
}

function renderUserActivityPieChart(activity) {
  const activeUsers = Number(activity.active_users || 0);
  const inactiveUsers = Number(activity.inactive_users || 0);

  if (userStatusPieChart) userStatusPieChart.destroy();
  userStatusPieChart = new Chart($('userStatusPieChart').getContext('2d'), {
    type: 'pie',
    data: {
      labels: ['Active Users', 'Inactive Users'],
      datasets: [
        {
          data: [activeUsers, inactiveUsers],
          backgroundColor: ['rgba(0,217,122,0.75)', 'rgba(255,77,77,0.75)'],
          borderColor: ['rgba(0,217,122,1)', 'rgba(255,77,77,1)'],
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: '#8b8fa8', font: { family: 'Outfit' } } },
      },
    },
  });
}
