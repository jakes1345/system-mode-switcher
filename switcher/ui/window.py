"""Main application window — HeaderBar, two-pane layout, apply logic."""

from __future__ import annotations

import threading
from datetime import datetime

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Notify", "0.7")
from gi.repository import Gdk, GLib, Gtk, Notify

from switcher import backend
from switcher.config import Config, ProfileConfig, TweakConfig, save_config
from switcher.ui.dialogs import (
    confirm_apply_dialog,
    confirm_delete_dialog,
    save_profile_dialog,
)
from switcher.ui.profile_sidebar import ProfileSidebar
from switcher.ui.service_panel import ServicePanel

Notify.init("System Mode Switcher")


class SwitcherWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, config: Config):
        super().__init__(application=app, title="System Mode Switcher")
        self.set_default_size(900, 700)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon_name("preferences-system")

        self._config = config
        self._active_profile: str | None = None

        self._build_headerbar()
        self._build_layout()
        self._setup_shortcuts()

        # Initial load
        self.panel.refresh_switches()
        self._detect_active_profile()
        self._update_system_stats()

        # Auto-refresh every 30s
        GLib.timeout_add_seconds(30, self._auto_refresh)

    # ── HeaderBar ─────────────────────────────────────────────────────────

    def _build_headerbar(self) -> None:
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.set_title("System Mode Switcher")
        hb.set_subtitle("Manage system profiles")

        # System stats on the right
        stats_box = Gtk.Box(spacing=12)

        ram_label = Gtk.Label(label="RAM:")
        ram_label.get_style_context().add_class("system-stat")
        stats_box.pack_start(ram_label, False, False, 0)

        self._ram_value = Gtk.Label(label="...")
        self._ram_value.get_style_context().add_class("system-stat-value")
        stats_box.pack_start(self._ram_value, False, False, 0)

        cpu_label = Gtk.Label(label="CPU:")
        cpu_label.get_style_context().add_class("system-stat")
        stats_box.pack_start(cpu_label, False, False, 0)

        self._cpu_value = Gtk.Label(label="...")
        self._cpu_value.get_style_context().add_class("system-stat-value")
        stats_box.pack_start(self._cpu_value, False, False, 0)

        # Refresh button
        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        refresh_btn.set_tooltip_text("Refresh status")
        refresh_btn.get_style_context().add_class("refresh-button")
        refresh_btn.connect("clicked", lambda _: self._full_refresh())
        stats_box.pack_start(refresh_btn, False, False, 0)

        hb.pack_end(stats_box)
        self.set_titlebar(hb)

    # ── Layout ────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Two-pane: sidebar + panel
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(230)

        self.sidebar = ProfileSidebar(
            profiles=self._config.profiles,
            on_select=self._on_profile_select,
            on_delete=self._on_profile_delete,
            on_save=self._on_save_profile,
        )
        paned.pack1(self.sidebar, resize=False, shrink=False)

        self.panel = ServicePanel(self._config)
        paned.pack2(self.panel, resize=True, shrink=False)

        outer.pack_start(paned, True, True, 0)

        # Bottom bar
        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        bottom.get_style_context().add_class("bottom-bar")

        # Progress bar
        self._progress = Gtk.ProgressBar()
        self._progress.set_no_show_all(True)
        bottom.pack_start(self._progress, False, False, 0)

        # Buttons row
        btn_row = Gtk.Box(spacing=10)
        btn_row.set_halign(Gtk.Align.CENTER)

        # Log expander
        self._log_buffer = Gtk.TextBuffer()
        log_expander = Gtk.Expander(label="Log")
        log_expander.get_style_context().add_class("log-expander")
        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        log_scroll.set_size_request(-1, 100)
        self._log_view = Gtk.TextView(buffer=self._log_buffer)
        self._log_view.set_editable(False)
        self._log_view.set_cursor_visible(False)
        self._log_view.get_style_context().add_class("log-view")
        log_scroll.add(self._log_view)
        log_expander.add(log_scroll)
        btn_row.pack_start(log_expander, True, True, 0)

        self._apply_btn = Gtk.Button(label="Apply Changes  (Ctrl+Enter)")
        self._apply_btn.get_style_context().add_class("apply-button")
        self._apply_btn.connect("clicked", self._on_apply)
        btn_row.pack_end(self._apply_btn, False, False, 0)

        bottom.pack_start(btn_row, False, False, 0)
        outer.pack_start(bottom, False, False, 0)

        self.add(outer)

    # ── Keyboard Shortcuts ────────────────────────────────────────────────

    def _setup_shortcuts(self) -> None:
        accel = Gtk.AccelGroup()
        self.add_accel_group(accel)

        profile_names = list(self._config.profiles.keys())
        for i, name in enumerate(profile_names[:9]):
            key = Gdk.keyval_from_name(str(i + 1))
            accel.connect(
                key, Gdk.ModifierType.CONTROL_MASK, 0,
                lambda _ag, _w, _k, _m, n=name: (self._on_profile_select(n), True)[-1],
            )

        accel.connect(
            Gdk.KEY_Return, Gdk.ModifierType.CONTROL_MASK, 0,
            lambda *_: (self._on_apply(self._apply_btn), True)[-1],
        )

    # ── Profile Actions ───────────────────────────────────────────────────

    def _on_profile_select(self, name: str) -> None:
        prof = self._config.profiles.get(name)
        if not prof:
            return
        self.panel.apply_profile(prof.services, prof.processes, prof.tweaks)
        self._active_profile = name
        self.sidebar.set_active_profile(name)
        self._log(f"Profile '{name}' selected — click Apply to activate.")

    def _on_profile_delete(self, name: str) -> None:
        prof = self._config.profiles.get(name)
        if not prof or prof.builtin:
            return
        if not confirm_delete_dialog(self, name):
            return
        del self._config.profiles[name]
        self.sidebar.remove_profile_card(name)
        save_config(self._config)
        if self._active_profile == name:
            self._active_profile = None
            self.sidebar.set_active_profile(None)
        self._log(f"Profile '{name}' deleted.")

    def _on_save_profile(self) -> None:
        result = save_profile_dialog(self)
        if not result:
            return
        name, color = result
        desired = self.panel.collect_desired_state()
        profile = ProfileConfig(
            name=name,
            description=f"Custom profile: {name}",
            color=color,
            builtin=False,
            services=desired["services"],
            processes=desired["processes"],
            tweaks=TweakConfig(
                swappiness=desired["swappiness"],
                compositor_unredirect=desired["unredirect"],
                gpu_performance=desired["gpu_perf"],
            ),
        )
        self._config.profiles[name] = profile
        save_config(self._config)
        self.sidebar.add_profile_card(profile)
        self._active_profile = name
        self.sidebar.set_active_profile(name)
        self._log(f"Profile '{name}' saved.")

    # ── Detect Active Profile ─────────────────────────────────────────────

    def _detect_active_profile(self) -> None:
        for name, prof in self._config.profiles.items():
            match = True
            for svc_name, desired in prof.services.items():
                if svc_name in self.panel.service_rows:
                    current = self.panel.service_rows[svc_name].switch.get_active()
                    if current != desired:
                        match = False
                        break
            if not match:
                continue
            for proc_id, desired in prof.processes.items():
                if proc_id in self.panel.process_rows:
                    current = self.panel.process_rows[proc_id].switch.get_active()
                    if current != desired:
                        match = False
                        break
            if match:
                self._active_profile = name
                self.sidebar.set_active_profile(name)
                self._log(f"Detected active profile: {name}")
                return
        self._log("No profile matches current state.")

    # ── Apply ─────────────────────────────────────────────────────────────

    def _on_apply(self, _button) -> None:
        desired = self.panel.collect_desired_state()
        changes = self._build_change_list(desired)

        if not changes:
            self._log("No changes to apply.")
            return

        if not confirm_apply_dialog(self, [c[1] for c in changes]):
            return

        self._apply_btn.set_sensitive(False)
        self._apply_btn.set_label("Applying...")
        self._progress.set_fraction(0)
        self._progress.show()

        thread = threading.Thread(
            target=self._apply_worker, args=(desired, changes), daemon=True
        )
        thread.start()

    def _build_change_list(self, desired: dict) -> list[tuple[str, str]]:
        """Build list of (type, description) for changes."""
        changes = []

        for svc_name, want in desired["services"].items():
            current = backend.is_service_active(svc_name)
            if want and not current:
                display = self.panel.service_rows[svc_name].name_label.get_text()
                changes.append(("start_svc", f"START  {display} ({svc_name})"))
            elif not want and current:
                display = self.panel.service_rows[svc_name].name_label.get_text()
                changes.append(("stop_svc", f"STOP   {display} ({svc_name})"))

        for proc_id, want in desired["processes"].items():
            proc = next((p for p in self._config.processes if p.id == proc_id), None)
            if not proc:
                continue
            current = backend.is_process_running(proc.grep)
            if want and not current:
                changes.append(("start_proc", f"START  {proc.display}"))
            elif not want and current:
                changes.append(("stop_proc", f"KILL   {proc.display}"))

        current_swap = backend.get_swappiness()
        if desired["swappiness"] != current_swap:
            changes.append(("swap", f"SET    swappiness {current_swap} -> {desired['swappiness']}"))

        if desired["unredirect"] != backend.get_compositor_unredirect():
            changes.append(("comp", f"SET    compositor unredirect -> {desired['unredirect']}"))

        gpu = backend.get_gpu_performance_mode()
        if gpu is not None and gpu != desired["gpu_perf"]:
            label = "max" if desired["gpu_perf"] else "adaptive"
            changes.append(("gpu", f"SET    GPU performance -> {label}"))

        return changes

    def _apply_worker(self, desired: dict, changes: list[tuple[str, str]]) -> None:
        """Background thread — applies changes via pkexec batch script."""
        total = len(changes)

        # Separate privileged vs user-level changes
        services_start = []
        services_stop = []
        procs_start = []
        procs_kill = []
        new_swap = None

        for change_type, desc in changes:
            if change_type == "start_svc":
                svc = desc.split("(")[-1].rstrip(")")
                services_start.append(svc)
            elif change_type == "stop_svc":
                svc = desc.split("(")[-1].rstrip(")")
                services_stop.append(svc)
            elif change_type == "start_proc":
                proc_name = desc.replace("START  ", "")
                proc = next(
                    (p for p in self._config.processes
                     if p.display == proc_name), None
                )
                if proc and proc.start_cmd:
                    procs_start.append((proc.id, proc.start_cmd))
            elif change_type == "stop_proc":
                proc_name = desc.replace("KILL   ", "")
                proc = next(
                    (p for p in self._config.processes
                     if p.display == proc_name), None
                )
                if proc:
                    procs_kill.append((proc.id, proc.grep))
            elif change_type == "swap":
                new_swap = desired["swappiness"]

        # Build and run privileged script
        needs_pkexec = services_start or services_stop or procs_kill or procs_start or new_swap is not None
        gpu_change = any(t == "gpu" for t, _ in changes)

        if needs_pkexec:
            script = backend.build_apply_script(
                services_to_start=services_start,
                services_to_stop=services_stop,
                processes_to_start=procs_start,
                processes_to_kill=procs_kill,
                swappiness=new_swap,
                compositor_unredirect=None,  # handled separately
                gpu_performance=desired["gpu_perf"] if gpu_change and backend.GPU_VENDOR == "amd" else None,
            )
            GLib.idle_add(self._log, "Running privileged operations...")
            ok, output = backend.run_apply_script(script)

            # Parse output for progress
            done = 0
            for line in output.splitlines():
                line = line.strip()
                if line and not line.startswith("[sudo]"):
                    done += 1
                    frac = min(done / total, 0.95)
                    GLib.idle_add(self._progress.set_fraction, frac)
                    GLib.idle_add(self._log, f"  {line}")

            if not ok:
                GLib.idle_add(self._log, f"ERROR: Some operations failed. {output}")

        # Compositor (user-level, no pkexec)
        if any(t == "comp" for t, _ in changes):
            ok, err = backend.set_compositor_unredirect(desired["unredirect"])
            val = "on" if desired["unredirect"] else "off"
            GLib.idle_add(self._log, f"  Compositor unredirect -> {val}")
            if not ok:
                GLib.idle_add(self._log, f"  FAILED: {err}")

        # NVIDIA GPU (user-level)
        if gpu_change and backend.GPU_VENDOR == "nvidia":
            ok, err = backend.set_nvidia_gpu_mode(desired["gpu_perf"])
            label = "max performance" if desired["gpu_perf"] else "adaptive"
            GLib.idle_add(self._log, f"  GPU -> {label}")
            if not ok:
                GLib.idle_add(self._log, f"  FAILED: {err}")

        GLib.idle_add(self._finish_apply, total)

    def _finish_apply(self, total: int) -> None:
        self._apply_btn.set_sensitive(True)
        self._apply_btn.set_label("Apply Changes  (Ctrl+Enter)")
        self._progress.set_fraction(1.0)
        GLib.timeout_add(2000, self._progress.hide)

        self.panel.refresh_switches()
        self._detect_active_profile()

        profile_msg = f" ({self._active_profile})" if self._active_profile else ""
        msg = f"Done! {total} change(s) applied{profile_msg}."
        self._log(msg)

        # Desktop notification
        try:
            n = Notify.Notification.new(
                "System Mode Switcher",
                msg,
                "preferences-system",
            )
            n.show()
        except Exception:
            pass

    # ── Auto-Refresh ──────────────────────────────────────────────────────

    def _auto_refresh(self) -> bool:
        """Called every 30s. Updates status dots and system stats only."""
        self.panel.refresh_status()
        self._update_system_stats()
        return True  # keep timer alive

    def _full_refresh(self) -> None:
        """Manual refresh — updates switches too."""
        self.panel.refresh_switches()
        self._update_system_stats()
        self._detect_active_profile()
        self._log("Status refreshed.")

    def _update_system_stats(self) -> None:
        def worker():
            used, total = backend.get_ram_info()
            cpu = backend.get_cpu_percent()
            GLib.idle_add(self._ram_value.set_text, f"{used}/{total} GB")
            GLib.idle_add(self._cpu_value.set_text, f"{cpu}%")

        threading.Thread(target=worker, daemon=True).start()

    # ── Logging ───────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        end = self._log_buffer.get_end_iter()
        self._log_buffer.insert(end, f"[{ts}] {msg}\n")
        mark = self._log_buffer.create_mark(None, self._log_buffer.get_end_iter(), False)
        self._log_view.scroll_mark_onscreen(mark)
