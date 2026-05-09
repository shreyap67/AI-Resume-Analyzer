/* ============================================================
   main.js – Global UI: sidebar toggle, flash auto-dismiss,
             logout confirmation, dot-loader animation.
   ============================================================ */

/* ── Sidebar mobile toggle ──────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {

  var sidebarToggle = document.getElementById('sidebarToggle');
  var sidebar       = document.getElementById('sidebar');

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('open');
    });
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function (e) {
      if (
        sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        e.target !== sidebarToggle
      ) {
        sidebar.classList.remove('open');
      }
    });
  }

  /* ── Auto-dismiss flash messages after 4 s ─────────────────── */
  var flashes = document.querySelectorAll('#flash-container .flash');
  flashes.forEach(function (flash, idx) {
    setTimeout(function () {
      flash.style.opacity   = '0';
      flash.style.transform = 'translateX(100%)';
      flash.style.transition = 'all 0.3s ease';
      setTimeout(function () { if (flash.parentNode) flash.remove(); }, 320);
    }, 4000 + idx * 200);
  });

  /* ── Animate progress bars ─────────────────────────────────── */
  document.querySelectorAll('.prog-fill[data-width]').forEach(function (bar) {
    var w = bar.getAttribute('data-width');
    setTimeout(function () { bar.style.width = w; }, 150);
  });

  /* ── Add dot-loader styles if not already in CSS ───────────── */
  if (!document.getElementById('dotLoaderStyle')) {
    var style = document.createElement('style');
    style.id = 'dotLoaderStyle';
    style.textContent = [
      '.dot-loader{display:flex;gap:6px;align-items:center;justify-content:center}',
      '.dot-loader span{width:10px;height:10px;border-radius:50%;',
      '  background:var(--grad-primary,linear-gradient(135deg,#00D1FF,#6C63FF));',
      '  animation:dotBounce 1.2s ease-in-out infinite}',
      '.dot-loader span:nth-child(2){animation-delay:.2s}',
      '.dot-loader span:nth-child(3){animation-delay:.4s}',
      '@keyframes dotBounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-10px)}}'
    ].join('');
    document.head.appendChild(style);
  }

});

/* ── Tag-animate styles ─────────────────────────────────────── */
(function () {
  var s = document.createElement('style');
  s.textContent = [
    '.tag-animate{animation:tagPop .25s cubic-bezier(.34,1.56,.64,1) both}',
    '@keyframes tagPop{from{opacity:0;transform:scale(.7)}to{opacity:1;transform:scale(1)}}'
  ].join('');
  document.head.appendChild(s);
})();

/* ── Logout Modal ───────────────────────────────────────────── */
/**
 * Premium animated logout confirmation modal.
 * Triggered by any element with id="logoutBtn" or id="logoutBtnNav".
 * Replaces the old browser confirm() dialog.
 */
(function () {
  function openLogoutModal(e) {
    e.preventDefault();
    const modal = document.getElementById('logoutModal');
    if (modal) modal.classList.add('show');
  }

  function closeLogoutModal() {
    const modal = document.getElementById('logoutModal');
    if (modal) modal.classList.remove('show');
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Sidebar logout button
    const btn = document.getElementById('logoutBtn');
    if (btn) btn.addEventListener('click', openLogoutModal);

    // Navbar avatar dropdown logout
    const btnNav = document.getElementById('logoutBtnNav');
    if (btnNav) btnNav.addEventListener('click', openLogoutModal);

    // Cancel button inside modal
    const cancelBtn = document.getElementById('cancelLogout');
    if (cancelBtn) cancelBtn.addEventListener('click', closeLogoutModal);

    // Click backdrop to dismiss
    const modal = document.getElementById('logoutModal');
    if (modal) {
      modal.addEventListener('click', function (e) {
        if (e.target === modal) closeLogoutModal();
      });
    }

    // ESC key to dismiss
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeLogoutModal();
    });
  });

  // Legacy shim — kept so any stray onclick="return confirmLogout(...)" won't crash
  window.confirmLogout = function (url) {
    const modal = document.getElementById('logoutModal');
    if (modal) {
      modal.classList.add('show');
    } else {
      // Fallback if modal not present
      if (window.confirm('Are you sure you want to log out?')) {
        window.location.href = url;
      }
    }
    return false;
  };
})();

/* ── animateScoreArc (used by charts.js + upload.js) ────────── */
function animateScoreArc(arcElement, score) {
  var circumference = 440; // 2π × r, where r = 70
  var offset = circumference - (score / 100) * circumference;
  arcElement.style.strokeDasharray  = circumference;
  arcElement.style.strokeDashoffset = circumference;
  arcElement.style.transition = 'stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1)';
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      arcElement.style.strokeDashoffset = offset;
    });
  });
}
