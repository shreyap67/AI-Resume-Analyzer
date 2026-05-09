/* ============================================================
   dashboard.js – Page-specific interactions:
     • Admin panel tab switching
     • History AJAX delete with fade-out
     • Profile form validation
     • Job matcher progress bar animations
     • Score circle animations on results page
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

  // ── Score arc animation on results page ───────────────────────
  var scoreArc = document.getElementById('scoreArc');
  if (scoreArc) {
    // The arc's stroke-dashoffset is already set server-side via Jinja2,
    // but we animate it in with a CSS transition trigger.
    var circumference = 415;

    // Read the current offset from the SVG attribute (set by server)
    var targetOffset = parseFloat(scoreArc.getAttribute('stroke-dashoffset') || circumference);

    // Start at full (empty arc), then animate to target
    scoreArc.style.strokeDashoffset = circumference;
    scoreArc.style.transition = 'stroke-dashoffset 1.3s cubic-bezier(0.4, 0, 0.2, 1)';

    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        scoreArc.style.strokeDashoffset = targetOffset;
      });
    });
  }

  // ── Animate stat value counters ───────────────────────────────
  function animateCounter(el) {
    var raw   = el.textContent.trim();
    var match = raw.match(/^([\d.]+)(%?)$/);
    if (!match) return;

    var target   = parseFloat(match[1]);
    var suffix   = match[2] || '';
    var isFloat  = raw.includes('.');
    var duration = 1100;
    var start    = performance.now();

    function step(now) {
      var elapsed  = now - start;
      var progress = Math.min(elapsed / duration, 1);
      var eased    = 1 - Math.pow(1 - progress, 3);
      var current  = target * eased;
      el.textContent = (isFloat ? current.toFixed(1) : Math.round(current)) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
  }

  document.querySelectorAll('.profile-stat-val, .score-stat-val').forEach(function (el) {
    if (/^[\d.]+%?$/.test(el.textContent.trim())) {
      animateCounter(el);
    }
  });

  // ── Progress bars deferred fill ───────────────────────────────
  // For bars on results and job matcher pages
  setTimeout(function () {
    document.querySelectorAll('.prog-fill').forEach(function (el) {
      var targetWidth = el.style.width;
      if (!targetWidth) return;
      el.style.width = '0%';
      setTimeout(function () {
        el.style.transition = 'width 1.1s cubic-bezier(0.4, 0, 0.2, 1)';
        el.style.width = targetWidth;
      }, 100);
    });
  }, 150);

  // ── Admin panel tab switching ─────────────────────────────────
  // (Also defined inline in admin_panel.html for simplicity,
  //  but we keep a version here for MPA navigation consistency)
  window.showAdminTab = function (name, clickedBtn) {
    document.querySelectorAll('.admin-tab-content').forEach(function (t) {
      t.classList.remove('active');
    });
    document.querySelectorAll('.admin-tab').forEach(function (t) {
      t.classList.remove('active');
    });
    var target = document.getElementById('tab-' + name);
    if (target) target.classList.add('active');
    if (clickedBtn) clickedBtn.classList.add('active');
  };

  // ── History: AJAX row delete ──────────────────────────────────
  window.deleteHistoryRow = function (id, url) {
    if (!confirm('Delete this analysis record permanently?')) return;

    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.success) {
        var row = document.getElementById('row-' + id);
        if (row) {
          row.style.opacity    = '0';
          row.style.transform  = 'translateX(-20px)';
          row.style.transition = 'all 0.3s ease';
          setTimeout(function () { row.remove(); }, 320);
        }
      }
    })
    .catch(function () {
      // Fall back to full page reload
      window.location.reload();
    });
  };

  // ── Profile form: client-side password match validation ───────
  var confirmPwInput = document.querySelector('input[name="confirm_password"]');
  var newPwInput     = document.querySelector('input[name="new_password"]');

  if (confirmPwInput && newPwInput) {
    confirmPwInput.addEventListener('input', function () {
      if (this.value && this.value !== newPwInput.value) {
        this.style.borderColor = 'rgba(239, 68, 68, 0.5)';
      } else {
        this.style.borderColor = '';
      }
    });
  }

  // ── Job matcher: highlight best match row ─────────────────────
  var firstRow = document.querySelector('.job-match-row');
  if (firstRow) {
    firstRow.style.borderColor = 'rgba(0, 209, 255, 0.25)';
    firstRow.style.background  = 'linear-gradient(90deg, rgba(0,209,255,0.03), rgba(124,58,237,0.03))';
  }

  // ── Saved resumes: save/unsave via fetch ──────────────────────
  document.querySelectorAll('[data-save-resume]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var resumeId = this.getAttribute('data-save-resume');
      var url      = '/resume/save/' + resumeId;
      var self     = this;

      fetch(url, { method: 'POST', credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.success) {
            self.textContent = data.is_saved ? '★ Saved' : '☆ Save';
          }
        });
    });
  });

  // ── Auto-hide flash on dashboard after 5s ─────────────────────
  setTimeout(function () {
    document.querySelectorAll('.flash').forEach(function (f) {
      f.style.opacity   = '0';
      f.style.transition = 'opacity 0.4s ease';
      setTimeout(function () { f.remove(); }, 420);
    });
  }, 5000);

});
