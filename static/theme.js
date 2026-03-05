/* ===========================
   Theme Management
   Handles dark/light toggle and localStorage persistence
   =========================== */

const THEME_KEY = 'fs-theme';
const LIGHT_CLASS = 'theme-light';

function applyStoredTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === 'light') {
        document.documentElement.classList.add(LIGHT_CLASS);
    } else {
        document.documentElement.classList.remove(LIGHT_CLASS);
    }
    _syncToggleBtn();
}

function toggleTheme() {
    const isLight = document.documentElement.classList.toggle(LIGHT_CLASS);
    localStorage.setItem(THEME_KEY, isLight ? 'light' : 'dark');
    _syncToggleBtn();
}

function _syncToggleBtn() {
    const btn = document.getElementById('themeToggleBtn');
    if (!btn) return;
    const isLight = document.documentElement.classList.contains(LIGHT_CLASS);
    btn.setAttribute('title', isLight ? 'Switch to dark mode' : 'Switch to light mode');
    btn.setAttribute('aria-label', isLight ? 'Switch to dark mode' : 'Switch to light mode');
    btn.querySelector('.theme-icon').textContent = isLight ? '🌙' : '☀️';
}

// Apply on load (fallback if inline script missed it)
applyStoredTheme();
