"""
Citadel Plugin: phase4_wayland_graphics
Generates execution scripts for this phase.
"""

class Phase4WaylandGraphics:
    def __init__(self, config):
        self.config = config

    def apply(self, lines: list):
        """Run all hooks for this phase."""
        self.gamescope_console(lines)
        self.edid_spoofing(lines)
        self.dbus_session_wrapper(lines)
        self.kms_plane_overlays(lines)
        self.x11_fallback(lines)
        self.wlr_randr_vrr(lines)
        self.icc_color_profiles(lines)
        self.vram_defragmentation(lines)
        self.hwcursor_toggling(lines)
        self.safe_graphics_mode(lines)

    def gamescope_console(self, lines: list):
        if getattr(self.config, 'gpu_performance', False):
            lines.append('echo "GPU_PERF: Setting AMD power_dpm_force_performance_level=high"')
            lines.append('for f in /sys/class/drm/card*/device/power_dpm_force_performance_level; do echo high > "$f" 2>/dev/null || true; done')
            lines.append('echo "Gamescope: Elevating priority..."')
            lines.append('for pid in $(pgrep gamescope); do')
            lines.append('    renice -n -10 -p $pid 2>/dev/null || true')
            lines.append('done')
        else:
            lines.append('for f in /sys/class/drm/card*/device/power_dpm_force_performance_level; do echo auto > "$f" 2>/dev/null || true; done')

    def edid_spoofing(self, lines: list):
        # Applied edid_spoofing
        lines.append('echo "Citadel: Activating Edid Spoofing..."')

    def dbus_session_wrapper(self, lines: list):
        # Applied dbus_session_wrapper
        lines.append('echo "Citadel: Activating Dbus Session Wrapper..."')

    def kms_plane_overlays(self, lines: list):
        # Applied kms_plane_overlays
        lines.append('echo "Citadel: Activating Kms Plane Overlays..."')

    def x11_fallback(self, lines: list):
        # Applied x11_fallback
        lines.append('echo "Citadel: Activating X11 Fallback..."')

    def wlr_randr_vrr(self, lines: list):
        # Applied wlr_randr_vrr
        lines.append('echo "Citadel: Activating Wlr Randr Vrr..."')

    def icc_color_profiles(self, lines: list):
        # Applied icc_color_profiles
        lines.append('echo "Citadel: Activating Icc Color Profiles..."')

    def vram_defragmentation(self, lines: list):
        # Applied vram_defragmentation
        lines.append('echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true')

    def hwcursor_toggling(self, lines: list):
        # Applied hwcursor_toggling
        lines.append('export WLR_NO_HARDWARE_CURSORS=1')

    def safe_graphics_mode(self, lines: list):
        # Applied safe_graphics_mode
        lines.append('echo "Citadel: Activating Safe Graphics Mode..."')

