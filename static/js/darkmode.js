/* ============================================================
   darkmode.js – Dark / Light theme toggle
   Persists user preference in localStorage.
   Applies the class to <html> so CSS variables switch globally.
   ============================================================ */

(function () {
  'use strict';

  var STORAGE_KEY = 'resumeai_theme';
  var DARK_CLASS  = 'dark-theme';
  var LIGHT_CLASS = 'light-theme';

  // ── Read saved preference or default to dark ──────────────────
  function getSavedTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'dark';
    } catch (e) {
      return 'dark';
    }
  }

  function saveTheme(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) { /* ignore quota errors */ }
  }

  // ── Apply theme to <html> and <body> ─────────────────────────
  function applyTheme(theme) {
    var html = document.documentElement;
    var body = document.body;

    if (theme === 'light') {
      html.classList.remove(DARK_CLASS);
      html.classList.add(LIGHT_CLASS);
      body.classList.remove(DARK_CLASS);
      body.classList.add(LIGHT_CLASS);
    } else {
      html.classList.remove(LIGHT_CLASS);
      html.classList.add(DARK_CLASS);
      body.classList.remove(LIGHT_CLASS);
      body.classList.add(DARK_CLASS);
    }

    updateToggleIcon(theme);
  }

  // ── Update the toggle button icon ────────────────────────────
  function updateToggleIcon(theme) {
    var icon = document.getElementById('themeIcon');
    if (icon) {
      icon.textContent = (theme === 'light') ? '☀️' : '🌙';
      // Update title for accessibility
      var btn = document.getElementById('themeToggle');
      if (btn) {
        btn.setAttribute('aria-label', theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode');
        btn.setAttribute('title', theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode');
      }
    }
  }

  // ── Toggle between dark and light ────────────────────────────
  function toggleTheme() {
    var current = getSavedTheme();
    var next    = (current === 'dark') ? 'light' : 'dark';
    saveTheme(next);
    applyTheme(next);
  }

  // ── Init: apply saved theme immediately to prevent flash ─────
  // This runs before DOMContentLoaded to avoid FOUC
  var savedTheme = getSavedTheme();
  applyTheme(savedTheme);

  // ── Bind toggle button once DOM is ready ─────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    var toggleBtn = document.getElementById('themeToggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', toggleTheme);
    }

    // Also expose globally for inline onclick use
    window.toggleTheme = toggleTheme;
  });

})();
