"""Application CSS — System Mode Switcher dark theme.

Design: Industrial control panel. Warm darks, no blue spam.
Each profile's color is the visual identity — the chrome stays neutral.
"""

CSS = """
/* ── Base — warm dark, not cold blue ──────────────────────────── */

window, .main-container {
    background-color: #0d0d0f;
}

headerbar {
    background: #161618;
    border-bottom: 1px solid #2a2a2c;
    padding: 4px 8px;
}

headerbar .title {
    color: #e8e4df;
    font-weight: bold;
    font-size: 15px;
    letter-spacing: 0.5px;
}

headerbar .subtitle {
    color: #6b6660;
    font-size: 11px;
}

.system-stat {
    color: #6b6660;
    font-size: 11px;
    font-family: monospace;
}

.system-stat-value {
    color: #d4a845;
    font-size: 11px;
    font-weight: bold;
    font-family: monospace;
}

/* ── Sidebar — dark panel ─────────────────────────────────────── */

.sidebar {
    background-color: #111113;
    border-right: 1px solid #222224;
}

.sidebar-title {
    color: #5a5550;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 3px;
}

.profile-card {
    background: #1a1a1c;
    border: none;
    border-left: 3px solid #333;
    border-radius: 0px 8px 8px 0px;
    padding: 10px 14px;
    margin: 1px 0;
}

.profile-card:hover {
    background: #222224;
}

.profile-card.active {
    background: #1e1e20;
}

.profile-card-name {
    color: #e0dcd6;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 0.3px;
}

.profile-card-desc {
    color: #5a5550;
    font-size: 10px;
    margin-top: 2px;
}

.save-profile-btn {
    background: transparent;
    border: 1px dashed #333;
    border-radius: 6px;
    padding: 8px 14px;
    color: #4a4540;
    font-size: 12px;
}

.save-profile-btn:hover {
    border-color: #d4a845;
    color: #d4a845;
}

/* ── Service Panel ────────────────────────────────────────────── */

.panel-bg {
    background-color: #0d0d0f;
}

.search-entry {
    background: #161618;
    color: #c8c4be;
    border: 1px solid #2a2a2c;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    caret-color: #d4a845;
}

.search-entry:focus {
    border-color: #d4a845;
}

.section-label {
    color: #6b6660;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 2px;
}

.service-row {
    background: #141416;
    border-left: 2px solid #252527;
    border-radius: 0px 6px 6px 0px;
    padding: 7px 12px;
    margin: 1px 0;
}

.service-row:hover {
    background: #1a1a1c;
}

.service-name {
    color: #d0ccc6;
    font-size: 12px;
    font-weight: 600;
}

.service-desc {
    color: #4a4540;
    font-size: 10px;
}

.status-dot {
    font-size: 9px;
}

.status-dot.on {
    color: #00e676;
}

.status-dot.off {
    color: #3a3835;
}

.tweak-label {
    color: #a09a92;
    font-size: 12px;
}

.tweak-row {
    background: #141416;
    border-left: 2px solid #252527;
    border-radius: 0px 6px 6px 0px;
    padding: 7px 12px;
    margin: 1px 0;
}

/* ── Bottom Bar ───────────────────────────────────────────────── */

.bottom-bar {
    background: #111113;
    border-top: 1px solid #222224;
    padding: 8px 16px;
}

.apply-button {
    background: #d4a845;
    color: #0d0d0f;
    border-radius: 6px;
    padding: 8px 28px;
    font-size: 13px;
    font-weight: bold;
    border: none;
    min-width: 200px;
    letter-spacing: 0.5px;
}

.apply-button:hover {
    background: #e0b94f;
}

.apply-button:disabled {
    background: #2a2a2c;
    color: #4a4540;
}

.refresh-button {
    background: transparent;
    color: #5a5550;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    border: 1px solid #2a2a2c;
}

.refresh-button:hover {
    background: #1a1a1c;
    color: #a09a92;
}

/* ── Progress Bar ─────────────────────────────────────────────── */

progressbar trough {
    background: #1a1a1c;
    border-radius: 3px;
    min-height: 4px;
}

progressbar progress {
    background: #d4a845;
    border-radius: 3px;
    min-height: 4px;
}

/* ── Log — green terminal ─────────────────────────────────────── */

.log-expander {
    color: #4a4540;
    font-size: 11px;
}

.log-view {
    background: #0a0a0c;
    color: #5a9a5a;
    font-family: monospace;
    font-size: 10px;
    border-radius: 4px;
    padding: 8px;
}

/* ── Dialogs ──────────────────────────────────────────────────── */

.dialog-label {
    color: #a09a92;
    font-size: 13px;
}

/* ── Switches ─────────────────────────────────────────────────── */

switch {
    background: #2a2a2c;
    border-radius: 10px;
    min-width: 36px;
    min-height: 18px;
}

switch:checked {
    background: #00c853;
}

switch slider {
    background: #c8c4be;
    border-radius: 9px;
    min-width: 16px;
    min-height: 16px;
}

/* ── Scale (swappiness slider) ────────────────────────────────── */

scale trough {
    background: #1a1a1c;
    border-radius: 3px;
    min-height: 4px;
}

scale trough highlight {
    background: #d4a845;
    border-radius: 3px;
    min-height: 4px;
}

scale slider {
    background: #d0ccc6;
    border-radius: 8px;
    min-width: 16px;
    min-height: 16px;
}

scale value {
    color: #6b6660;
    font-size: 10px;
}

/* ── Scrollbar ────────────────────────────────────────────────── */

scrollbar {
    background: transparent;
}

scrollbar slider {
    background: #2a2a2c;
    border-radius: 4px;
    min-width: 6px;
}

scrollbar slider:hover {
    background: #3a3a3c;
}

/* ── Separator ────────────────────────────────────────────────── */

separator {
    background: #1a1a1c;
    min-height: 1px;
}
"""
