"""Application CSS — dark theme for System Mode Switcher."""

CSS = """
/* ── Base ──────────────────────────────────────────────────────── */

window, .main-container {
    background-color: #0f0f1a;
}

headerbar {
    background: linear-gradient(to right, #1a1a2e, #16213e);
    border-bottom: 1px solid #2a2a4a;
    padding: 4px 8px;
}

headerbar .title {
    color: #e0e0e0;
    font-weight: bold;
    font-size: 15px;
}

headerbar .subtitle {
    color: #666;
    font-size: 11px;
}

.system-stat {
    color: #888;
    font-size: 12px;
    font-family: monospace;
}

.system-stat-value {
    color: #4fc3f7;
    font-size: 12px;
    font-weight: bold;
    font-family: monospace;
}

/* ── Sidebar ──────────────────────────────────────────────────── */

.sidebar {
    background-color: #111122;
    border-right: 1px solid #2a2a4a;
}

.sidebar-title {
    color: #666;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 2px;
}

.profile-card {
    background: #1a1a2e;
    border: 2px solid #2a2a4a;
    border-radius: 10px;
    padding: 12px 14px;
    transition: all 200ms ease;
}

.profile-card:hover {
    background: #1e1e3a;
    border-color: #444;
}

.profile-card.active {
    background: #1a1a3e;
    border-width: 2px;
}

.profile-card-name {
    color: #e0e0e0;
    font-size: 14px;
    font-weight: bold;
}

.profile-card-desc {
    color: #777;
    font-size: 11px;
}

.save-profile-btn {
    background: transparent;
    border: 2px dashed #333;
    border-radius: 10px;
    padding: 10px 14px;
    color: #555;
    font-size: 13px;
}

.save-profile-btn:hover {
    border-color: #4fc3f7;
    color: #4fc3f7;
}

/* ── Service Panel ────────────────────────────────────────────── */

.panel-bg {
    background-color: #0f0f1a;
}

.search-entry {
    background: #1a1a2e;
    color: #e0e0e0;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
}

.search-entry:focus {
    border-color: #4fc3f7;
}

.section-label {
    color: #4fc3f7;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 1px;
}

.service-row {
    background: #161628;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 2px 0;
}

.service-row:hover {
    background: #1c1c38;
}

.service-name {
    color: #e0e0e0;
    font-size: 13px;
    font-weight: 600;
}

.service-desc {
    color: #555;
    font-size: 11px;
}

.status-dot {
    font-size: 10px;
}

.status-dot.on {
    color: #2ecc71;
}

.status-dot.off {
    color: #555;
}

.tweak-label {
    color: #ccc;
    font-size: 13px;
}

.tweak-row {
    background: #161628;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 2px 0;
}

/* ── Bottom Bar ───────────────────────────────────────────────── */

.bottom-bar {
    background: #111122;
    border-top: 1px solid #2a2a4a;
    padding: 8px 16px;
}

.apply-button {
    background: #4fc3f7;
    color: #0f0f1a;
    border-radius: 8px;
    padding: 8px 24px;
    font-size: 14px;
    font-weight: bold;
    border: none;
    min-width: 200px;
}

.apply-button:hover {
    background: #81d4fa;
}

.apply-button:disabled {
    background: #333;
    color: #666;
}

.refresh-button {
    background: #1a1a2e;
    color: #888;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    border: 1px solid #2a2a4a;
}

.refresh-button:hover {
    background: #2a2a4a;
    color: #ccc;
}

/* ── Progress Bar ─────────────────────────────────────────────── */

progressbar trough {
    background: #1a1a2e;
    border-radius: 4px;
    min-height: 6px;
}

progressbar progress {
    background: #4fc3f7;
    border-radius: 4px;
    min-height: 6px;
}

/* ── Log ──────────────────────────────────────────────────────── */

.log-expander {
    color: #555;
    font-size: 12px;
}

.log-view {
    background: #0a0a14;
    color: #58a6ff;
    font-family: monospace;
    font-size: 11px;
    border-radius: 6px;
    padding: 8px;
}

/* ── Dialogs ──────────────────────────────────────────────────── */

.dialog-label {
    color: #ccc;
    font-size: 13px;
}

/* ── Switches ─────────────────────────────────────────────────── */

switch {
    background: #2a2a4a;
    border-radius: 12px;
    min-width: 40px;
    min-height: 20px;
}

switch:checked {
    background: #4fc3f7;
}

switch slider {
    background: #e0e0e0;
    border-radius: 10px;
    min-width: 18px;
    min-height: 18px;
}
"""
