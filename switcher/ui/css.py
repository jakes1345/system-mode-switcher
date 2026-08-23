"""
Obsidian Citadel Apex Theme — ShadowSync Revision.
Variable-driven glass dashboard aligned with the ShadowCypher ecosystem.
"""

CSS = """
/* ── COLOR SYSTEM (Apex Standard) ── */
@define-color bg_void #060a10;
@define-color bg_obsidian #0a0f1a;
@define-color bg_surface #111827;
@define-color border_glow rgba(0, 242, 255, 0.4);

@define-color accent_cyan #00d4ff;
@define-color accent_violet #8b5cf6;
@define-color accent_rose #f43f5e;
@define-color accent_amber #f59e0b;
@define-color accent_green #10b981;

@define-color text_primary #f1f5f9;
@define-color text_secondary #94a3b8;
@define-color text_muted #475569;

* { 
    color: @text_primary;
    font-family: 'Inter', 'Ubuntu', sans-serif;
}

window {
    background-color: @bg_void;
}

/* ── HEADERBAR: COMMAND CENTER ── */

.citadel-header {
    background: linear-gradient(180deg, #0d1117 0%, @bg_obsidian 100%);
    border-bottom: 1px solid rgba(0, 212, 255, 0.15);
    padding: 4px 16px;
    min-height: 52px;
}

.citadel-title {
    font-size: 14px;
    font-weight: 900;
    letter-spacing: 3px;
    color: @accent_cyan;
}

.citadel-subtitle {
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 2px;
    color: @text_muted;
}

.citadel-stat {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 10px;
    color: @text_secondary;
    letter-spacing: 0.5px;
}

/* ── TACTICAL TYPOGRAPHY ── */

.section-label {
    color: @text_muted;
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 2px;
    margin-bottom: 8px;
}

.mono-meter {
    font-family: 'JetBrains Mono', 'Fira Code', 'monospace';
    font-size: 11px;
    color: @accent_cyan;
    letter-spacing: 1px;
}

.heavy-load {
    font-family: 'JetBrains Mono', 'Fira Code', 'monospace';
    font-size: 10px;
    color: @accent_rose;
    letter-spacing: 0.5px;
    font-weight: 700;
}

/* ── SIDEBAR: APEX CARDS ── */

.sidebar {
    background-color: @bg_obsidian;
    border-right: 1px solid rgba(255,255,255,0.05);
}

.sidebar-title {
    font-size: 11px;
    font-weight: 900;
    letter-spacing: 3px;
    color: @text_muted;
}

.profile-sidebar {
    background-color: @bg_obsidian;
    border-right: 1px solid rgba(255,255,255,0.05);
    padding: 10px 0;
}

.profile-card {
    background-color: @bg_surface;
    border: 1px solid rgba(255,255,255,0.08);
    border-left: 3px solid @accent_cyan;
    margin: 6px 12px;
    padding: 14px;
    border-radius: 12px;
    transition: all 200ms ease;
}

.profile-card:hover { border-color: @accent_cyan; }
.profile-card.active {
    background: linear-gradient(135deg, alpha(@accent_violet, 0.2) 0%, transparent 100%);
    border-color: @accent_cyan;
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.1);
}

.profile-card-name {
    font-weight: 800;
    font-size: 13px;
    color: @text_primary;
}

.profile-card-desc {
    font-size: 10px;
    color: @text_secondary;
    margin-top: 2px;
}

.save-profile-btn {
    background-color: @bg_surface;
    border: 1px dashed rgba(0, 212, 255, 0.3);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 11px;
    color: @accent_cyan;
    transition: all 200ms ease;
}

.save-profile-btn:hover {
    background-color: alpha(@accent_cyan, 0.1);
    border-color: @accent_cyan;
}

/* ── HARDWARE NUCLEUS: NEON GRID ── */

.core-node {
    margin: 4px;
    background-color: rgba(2, 6, 23, 0.6);
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.08);
    min-width: 60px;
    min-height: 60px;
    transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

.core-node.load-standby { 
    background-color: rgba(2, 6, 23, 0.8); 
    border-color: rgba(255, 255, 255, 0.05);
    box-shadow: inset 0 0 10px rgba(255, 255, 255, 0.02);
}

.core-node.load-low { 
    background-color: rgba(2, 6, 23, 0.6); 
    border-color: rgba(0, 212, 255, 0.1);
    box-shadow: 0 0 5px rgba(0, 212, 255, 0.1);
}

.core-node.load-med { background-color: @accent_green; box-shadow: 0 0 12px @accent_green; border-color: @accent_green; }
.core-node.load-high { background-color: @accent_amber; box-shadow: 0 0 15px @accent_amber; border-color: @accent_amber; }
.core-node.load-max { background-color: @accent_rose; box-shadow: 0 0 20px @accent_rose; border-color: @accent_rose; }

/* ── SERVICE PANEL ── */

.panel-bg { background-color: @bg_obsidian; }

.search-entry {
    background-color: @bg_surface;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 8px;
    color: @text_primary;
}

.service-row {
    padding: 12px 18px;
    border-bottom: 2px solid rgba(255,255,255,0.02);
}

.service-name {
    font-weight: 700;
    font-size: 12px;
    color: @text_primary;
}

.service-desc {
    font-size: 10px;
    color: @text_muted;
}

/* ── STATUS INDICATORS ── */

.status-dot {
    font-size: 12px;
}

.status-dot.on {
    color: @accent_green;
    text-shadow: 0 0 6px @accent_green;
}

.status-dot.off {
    color: @accent_rose;
    text-shadow: 0 0 4px alpha(@accent_rose, 0.3);
}

/* ── SWITCHES ── */

switch {
    background-color: @bg_surface;
    border: 1px solid @text_muted;
    border-radius: 20px;
    min-width: 40px;
    min-height: 20px;
}

switch:checked {
    background-color: @accent_cyan;
    border-color: @accent_cyan;
}

switch slider {
    border-radius: 50%;
    min-width: 16px;
    min-height: 16px;
    background-color: @text_primary;
}

/* ── HARDWARE COCKPIT TWEAKS ── */

.tweak-row {
    padding: 8px 4px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
}

.tweak-label {
    font-size: 11px;
    font-weight: 600;
    color: @text_secondary;
}

scale trough {
    background-color: @bg_surface;
    border-radius: 4px;
    min-height: 6px;
}

scale highlight {
    background-color: @accent_cyan;
    border-radius: 4px;
}

scale slider {
    background-color: @accent_cyan;
    border-radius: 50%;
    min-width: 14px;
    min-height: 14px;
    box-shadow: 0 0 6px @accent_cyan;
}

combobox button {
    background-color: @bg_surface;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
}

/* ── BOTTOM ACTION BAR ── */

.bottom-bar {
    background-color: @bg_obsidian;
    border-top: 1px solid rgba(255,255,255,0.05);
    padding: 10px;
}

.apply-button {
    background: linear-gradient(135deg, @accent_cyan 0%, @accent_violet 100%);
    color: #020617;
    font-weight: 900;
    font-size: 12px;
    letter-spacing: 2px;
    padding: 10px 28px;
    border-radius: 8px;
    border: none;
    transition: all 200ms ease;
}

.apply-button:hover {
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
}

.apply-button:disabled {
    background: @bg_surface;
    color: @text_muted;
}

/* ── PROGRESS BAR ── */

progressbar trough {
    background-color: @bg_surface;
    border-radius: 4px;
    min-height: 4px;
}

progressbar progress {
    background: linear-gradient(90deg, @accent_cyan 0%, @accent_violet 100%);
    border-radius: 4px;
    min-height: 4px;
    transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* ── LOG CONSOLE: VOID THEME ── */

.log-view {
    background-color: @bg_void;
    color: @text_primary;
    font-family: 'JetBrains Mono', 'monospace';
    font-size: 11px;
    padding: 10px;
}

textview text {
     background-color: @bg_void;
}

scrolledwindow viewport {
    background-color: transparent;
}

/* ── LEVEL BAR (Disk Pressure) ── */

levelbar block.filled {
    background-color: @accent_cyan;
    border-radius: 2px;
    transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

levelbar block.empty {
    background-color: @bg_surface;
}

levelbar trough {
    background-color: @bg_surface;
    border-radius: 4px;
    min-height: 10px;
}

/* ── SEPARATORS ── */

separator {
    background-color: rgba(255,255,255,0.05);
    min-height: 1px;
}

/* ── DIALOG STYLING ── */

dialog {
    background-color: @bg_obsidian;
}

.dialog-label {
    font-weight: 700;
    font-size: 12px;
    color: @text_secondary;
}

/* ── EXPANDER (Log Console) ── */

expander title {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 2px;
    color: @text_muted;
}

/* ── MAIN CONTAINER ── */

.main-container {
    background-color: @bg_void;
}

/* ── SCROLLBAR STYLING ── */

scrollbar slider {
    min-width: 6px;
    border-radius: 3px;
    background-color: rgba(255,255,255,0.1);
}

scrollbar slider:hover {
    background-color: rgba(0, 212, 255, 0.3);
}

scrollbar trough {
    background-color: transparent;
}

/* ── BUTTON GENERAL ── */

button {
    background-color: @bg_surface;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 6px;
    padding: 4px 8px;
    transition: all 150ms ease;
}

button:hover {
    background-color: alpha(@accent_cyan, 0.1);
    border-color: @accent_cyan;
}

headerbar button {
    background-color: transparent;
    border: none;
}

headerbar button:hover {
    background-color: alpha(@accent_cyan, 0.1);
}
"""
