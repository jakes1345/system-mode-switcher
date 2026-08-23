"""Main application window — HeaderBar, two-pane layout, apply logic."""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime
from pathlib import Path

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

Notify.init("Obsidian Citadel")


class SwitcherWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, config: Config):
        super().__init__(application=app, title="Obsidian Citadel")
        self.set_default_size(1100, 750)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # ── Visual Identity ──────────────────────────────────────────────────
        try:
            root = Path(__file__).parent.parent
            paths = [
                root / "assets" / "icon.png",        # primary — always exists
                root / "assets" / "citadel-apex.png",
                root / "assets" / "citadel_icon.png",
            ]
            
            icon_path = None
            for p in paths:
                if p.exists():
                    icon_path = str(p)
                    break
            
            if icon_path:
                self.set_icon_from_file(icon_path)
            else:
                self.set_icon_name("preferences-system")
        except (OSError, RuntimeError):
            self.set_icon_name("preferences-system")

        self._config = config
        self._active_profile: str | None = None
        self._sudo_password: str | None = None

        self._build_layout()
        self._setup_shortcuts()

        self._start_telemetry_heartbeat()
        self._async_initial_refresh()

        GLib.timeout_add_seconds(30, self._auto_refresh)

    def _async_initial_refresh(self) -> None:
        self.panel.refresh_switches(on_done=self._detect_active_profile)

    # ── HeaderBar ─────────────────────────────────────────────────────────

    def _build_headerbar(self) -> Gtk.HeaderBar:
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.get_style_context().add_class("citadel-header")
        
        # Left side: Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        title = Gtk.Label(label="OBSIDIAN CITADEL")
        title.get_style_context().add_class("citadel-title")
        subtitle = Gtk.Label(label="SYSTEM ANALYTICS & MODE CONTROL")
        subtitle.get_style_context().add_class("citadel-subtitle")
        title_box.pack_start(title, False, False, 0)
        title_box.pack_start(subtitle, False, False, 0)
        hb.set_custom_title(title_box)

        # Right side: Core Vitals
        vitals_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        
        # Hub Status
        self.hub_status_label = Gtk.Label(label="🔴 HUB OFFLINE")
        self.hub_status_label.get_style_context().add_class("citadel-stat")
        vitals_box.pack_start(self.hub_status_label, False, False, 0)

        # GPU Detail
        self.gpu_vitals_label = Gtk.Label()
        self.gpu_vitals_label.get_style_context().add_class("citadel-stat")
        vitals_box.pack_start(self.gpu_vitals_label, False, False, 0)

        # Global CPU/RAM
        self.ram_cpu_label = Gtk.Label()
        self.ram_cpu_label.get_style_context().add_class("citadel-stat")
        vitals_box.pack_start(self.ram_cpu_label, False, False, 0)

        # Refresh button
        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        refresh_btn.connect("clicked", lambda _: self._full_refresh())
        vitals_box.pack_start(refresh_btn, False, False, 0)

        hb.pack_end(vitals_box)
        return hb

    # ── Layout ────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        # HeaderBar — built ONCE
        self.set_titlebar(self._build_headerbar())

        # Main layout: 3 columns × 2 rows
        # ┌──────────┬──────────────┬─────────────┐
        # │          │              │             │
        # │ sidebar  │   panel      │  telemetry  │
        # │ (220px)  │   (expand)   │  (320px)    │
        # │          ├──────────────┤             │
        # │          │  bottom bar  │             │
        # └──────────┴──────────────┴─────────────┘
        self.main_grid = Gtk.Grid()
        self.main_grid.set_column_spacing(0)
        self.main_grid.set_row_spacing(0)
        self.main_grid.get_style_context().add_class("main-container")
        self.add(self.main_grid)

        # 1. Sidebar (Profiles) — fixed width, spans both rows
        self.sidebar = ProfileSidebar(
            profiles=self._config.profiles,
            on_select=self._on_profile_select,
            on_delete=self._on_profile_delete,
            on_save=self._on_save_profile,
        )
        self.sidebar.set_hexpand(False)
        self.sidebar.set_vexpand(True)
        self.main_grid.attach(self.sidebar, 0, 0, 1, 2)

        # 2. Service Matrix — center, EXPANDS to fill all extra space
        self.panel = ServicePanel(self._config)
        self.panel.set_hexpand(True)
        self.panel.set_vexpand(True)
        self.main_grid.attach(self.panel, 1, 0, 1, 1)

        # 3. Telemetry Hub — fixed width, spans both rows
        self.telemetry_hub = self._build_citadel_telemetry()
        self.telemetry_hub.set_hexpand(False)
        self.telemetry_hub.set_vexpand(True)
        self.telemetry_hub.set_size_request(320, -1)
        self.main_grid.attach(self.telemetry_hub, 2, 0, 1, 2)

        # 4. Bottom Action Bar — under center column only, no extra vexpand
        self.bottom_bar = self._build_bottom_bar()
        self.bottom_bar.set_hexpand(True)
        self.bottom_bar.set_vexpand(False)
        self.main_grid.attach(self.bottom_bar, 1, 1, 1, 1)

    def _build_citadel_telemetry(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.get_style_context().add_class("panel-bg")
        box.set_hexpand(True)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)

        # ── TACTICAL PULSE (60Hz Logic) ──
        pulse_label = Gtk.Label(label="TACTICAL PULSE")
        pulse_label.get_style_context().add_class("section-label")
        box.pack_start(pulse_label, False, False, 0)
        
        self.pulse_cpu = Gtk.Label(label="CPU_LOAD: [..........] 0%")
        self.pulse_mem = Gtk.Label(label="MEM_PRESSURE: [..........] 0%")
        self.pulse_net = Gtk.Label(label="NET_ENTROPY: 0.00bps")
        
        for lbl in [self.pulse_cpu, self.pulse_mem, self.pulse_net]:
            lbl.get_style_context().add_class("mono-meter")
            lbl.set_halign(Gtk.Align.START)
            box.pack_start(lbl, False, False, 2)
            
        self.heavy_load_label = Gtk.Label(label="")
        self.heavy_load_label.get_style_context().add_class("heavy-load")
        self.heavy_load_label.set_halign(Gtk.Align.START)
        box.pack_start(self.heavy_load_label, False, False, 4)

        # ── CPU NUCLEUS ──
        cl = Gtk.Label(label="HARDWARE NUCLEUS")
        cl.get_style_context().add_class("section-label")
        cl.set_margin_top(20)
        box.pack_start(cl, False, False, 0)

        self.core_grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        self.core_grid.set_halign(Gtk.Align.CENTER)
        self.core_nodes = []
        self._core_load_classes: list[str] = []
        self._cpu_count = os.cpu_count() or 12  # 12 for Ryzen 5 3600
        _cols = 4  # 4 cols → 3 rows for 12 CPUs
        for i in range(self._cpu_count):
            node = Gtk.Box()
            node.set_size_request(56, 56)
            node.get_style_context().add_class("core-node")
            self.core_grid.attach(node, i % _cols, i // _cols, 1, 1)
            self.core_nodes.append(node)
            self._core_load_classes.append("")
        box.pack_start(self.core_grid, False, False, 0)

        # Disk Pressure
        dk_label = Gtk.Label(label="DISK FLOW PRESSURE")
        dk_label.get_style_context().add_class("section-label")
        dk_label.set_margin_top(20)
        box.pack_start(dk_label, False, False, 0)
        
        self.disk_bar = Gtk.LevelBar()
        self.disk_bar.set_min_value(0)
        self.disk_bar.set_max_value(100)
        box.pack_start(self.disk_bar, False, False, 0)

        return box

    def _build_bottom_bar(self) -> Gtk.Box:
        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        bottom.get_style_context().add_class("bottom-bar")
        bottom.set_margin_bottom(10)

        # Progress bar
        self._progress = Gtk.ProgressBar()
        self._progress.set_no_show_all(True)
        bottom.pack_start(self._progress, False, False, 0)

        # Buttons row
        btn_row = Gtk.Box(spacing=10)
        btn_row.set_halign(Gtk.Align.CENTER)

        # Log expander
        self._log_buffer = Gtk.TextBuffer()
        log_expander = Gtk.Expander(label="LOG CONSOLE")
        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_size_request(-1, 80)
        self._log_view = Gtk.TextView(buffer=self._log_buffer)
        self._log_view.set_editable(False)
        self._log_view.get_style_context().add_class("log-view")
        log_scroll.add(self._log_view)
        log_expander.add(log_scroll)
        btn_row.pack_start(log_expander, True, True, 0)

        self._apply_btn = Gtk.Button(label="Apply Changes  (Ctrl+Enter)")
        self._apply_btn.get_style_context().add_class("apply-button")
        self._apply_btn.connect("clicked", self._on_apply)
        
        shortcut_lbl = Gtk.Label(label="Switch Profiles: Ctrl+1..9")
        shortcut_lbl.get_style_context().add_class("citadel-subtitle")
        shortcut_lbl.set_margin_end(15)
        
        btn_row.pack_end(self._apply_btn, False, False, 0)
        btn_row.pack_end(shortcut_lbl, False, False, 0)

        bottom.pack_start(btn_row, False, False, 0)
        return bottom

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
                cpu_governor=desired.get("cpu_gov", "performance"),
                gpu_power_limit=desired.get("gpu_pl"),
                thp_mode=desired.get("thp", "madvise"),
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
        if not self._active_profile:
            self._log("No profile selected.")
            return

        if not confirm_apply_dialog(self, [f"Deploy {self._active_profile} profile via Hub?"]):
            return

        self._apply_btn.set_sensitive(False)
        self._apply_btn.set_label("Applying via Citadel Hub...")
        self._progress.set_fraction(0.5)
        self._progress.show()

        thread = threading.Thread(target=self._apply_grpc_worker, args=(self._active_profile,), daemon=True)
        thread.start()

    def _apply_grpc_worker(self, profile_name: str) -> None:
        import grpc
        import os, sys
        hub_path = os.path.join(os.path.dirname(__file__), '../../services/hub')
        if hub_path not in sys.path: sys.path.insert(0, hub_path)
        import citadel_pb2
        import citadel_pb2_grpc
        
        try:
            channel = grpc.insecure_channel('localhost:50051')
            stub = citadel_pb2_grpc.CitadelServiceStub(channel)
            req = citadel_pb2.SetProfileRequest(profile_name=profile_name)
            resp = stub.SetProfile(req)
            GLib.idle_add(self._log, f"Hub Response: {resp.message}")
            ok = resp.success
        except Exception as e:
            GLib.idle_add(self._log, f"Hub Error: {e}")
            ok = False

        GLib.idle_add(self._finish_apply, ok)

    def _finish_apply(self, ok: bool) -> None:
        self._apply_btn.set_sensitive(True)
        self._apply_btn.set_label("Apply Changes  (Ctrl+Enter)")
        self._progress.set_fraction(1.0 if ok else 0.0)
        GLib.timeout_add(2000, lambda: (self._progress.hide(), False)[-1])

        self.panel.refresh_switches(on_done=self._detect_active_profile)

        msg = f"Done! Profile applied." if ok else "Failed to apply profile."
        self._log(msg)

        try:
            n = Notify.Notification.new("Obsidian Citadel", msg, "preferences-system")
            n.show()
        except Exception:
            pass

    # ── Auto-Refresh ──────────────────────────────────────────────────────

    def _auto_refresh(self) -> bool:
        """Called every 30s. Updates status dots only in background thread."""
        self.panel.refresh_status()
        return True  # keep timer alive

    def _full_refresh(self) -> None:
        """Manual refresh — updates switches and profile detection."""
        self.panel.refresh_switches(on_done=self._detect_active_profile)
        self._log("Status refreshed.")

    def _start_telemetry_heartbeat(self) -> None:
        """High-Performance Telemetry Loop — Native Thread Sampling."""
        if hasattr(self, "_heartbeat_active"): return
        self._heartbeat_active = True
        def _apply_vitals_to_ui(vitals: dict) -> bool:
            # 1. Update Mono Meters (Apex Pulse)
            if not getattr(self, "_hub_connected", False):
                self._hub_connected = True
                self.hub_status_label.set_text("🟢 HUB CONNECTED")
            
            cpu = vitals['cpu_total']
            mem = vitals['mem_percent']
            
            cpu = max(0, min(100, cpu))
            mem = max(0, min(100, mem))
            
            cpu_filled = max(0, min(10, int(cpu / 10)))
            cpu_empty = max(0, 10 - cpu_filled)
            self.pulse_cpu.set_text(f"CPU_LOAD: [{'|'*cpu_filled}{'.'*cpu_empty}] {cpu}%")
            
            mem_filled = max(0, min(10, int(mem / 10)))
            mem_empty = max(0, 10 - mem_filled)
            self.pulse_mem.set_text(f"MEM_PRESSURE: [{'|'*mem_filled}{'.'*mem_empty}] {mem}%")
            self.pulse_net.set_text(f"NET_ENTROPY: {vitals['net_speed']} KB/s")

            # 2. Update Legacy Labels (Header)
            self.ram_cpu_label.set_text(f"CPU: {cpu}%  |  RAM: {vitals['ram_used']}/{vitals['ram_total']} GB")

            # 3. Update GPU
            v = vitals['gpu']
            vram_gb = round(v["vram_used"] / (1024**3), 1) if v["vram_total"] > 0 else 0
            vram_tot = round(v["vram_total"] / (1024**3), 1) if v["vram_total"] > 0 else 0
            self.gpu_vitals_label.set_text(f"GPU: {v['temp']}°C  |  {int(v['utilization'])}% Util  |  {int(v['fan'])}% Fan  |  VRAM: {vram_gb}/{vram_tot} GB  |  {int(v['power'])}W")
            
            # Top process
            if vitals.get('top_process') and cpu > 15:
                self.heavy_load_label.set_text(f"HEAVY_LOAD: {vitals['top_process']}")
            else:
                self.heavy_load_label.set_text("")

            # 4. Update Nucleus — only mutate CSS when bucket actually changes
            for i, val in enumerate(vitals['cores'][:self._cpu_count]):
                if i >= len(self.core_nodes):
                    break
                if val >= 90: target = "load-max"
                elif val >= 65: target = "load-high"
                elif val >= 30: target = "load-med"
                elif val >= 10:  target = "load-low"
                elif val > 0: target = "load-standby"
                else:          target = ""
                if target == self._core_load_classes[i]:
                    continue
                ctx = self.core_nodes[i].get_style_context()
                if self._core_load_classes[i]:
                    ctx.remove_class(self._core_load_classes[i])
                if target:
                    ctx.add_class(target)
                self._core_load_classes[i] = target

            self.disk_bar.set_value(vitals['disk_pressure'])
            return False

        def telemetry_worker():
            """Hardware sampling engine via gRPC stream."""
            import grpc
            import os, sys
            hub_path = os.path.join(os.path.dirname(__file__), '../../services/hub')
            if hub_path not in sys.path: sys.path.insert(0, hub_path)
            import citadel_pb2
            import citadel_pb2_grpc
            
            while True:
                channel = None
                try:
                    channel = grpc.insecure_channel('localhost:50051')
                    stub = citadel_pb2_grpc.CitadelServiceStub(channel)
                    req = citadel_pb2.TelemetryRequest(interval_ms=1000)
                    for pulse in stub.StreamTelemetry(req):
                        cpu_cores = list(pulse.cpu.core_usage)
                        data = {
                            "cpu_total": int(sum(cpu_cores)/len(cpu_cores)) if cpu_cores else 0,
                            "mem_percent": int((pulse.ram.used_bytes / pulse.ram.total_bytes) * 100) if pulse.ram.total_bytes else 0,
                            "ram_used": round(pulse.ram.used_bytes / (1024**3), 1),
                            "ram_total": round(pulse.ram.total_bytes / (1024**3), 1),
                            "gpu": {
                                "temp": pulse.gpu.temperature,
                                "power": pulse.gpu.power_draw_watts,
                                "vram_used": pulse.gpu.vram_used_bytes,
                                "vram_total": pulse.gpu.vram_total_bytes,
                                "utilization": pulse.gpu.utilization_percent,
                                "fan": pulse.gpu.fan_speed_percent,
                            },
                            "cores": cpu_cores,
                            "disk_pressure": pulse.disk_pressure,
                            "net_speed": round((pulse.net_speed_bytes_sec / 1024), 1),
                            "top_process": pulse.top_process
                        }
                        GLib.idle_add(_apply_vitals_to_ui, data)
                except Exception:
                    def _set_offline():
                        if getattr(self, "_hub_connected", True):
                            self._hub_connected = False
                            self.hub_status_label.set_text("🔴 HUB OFFLINE")
                        return False
                    GLib.idle_add(_set_offline)
                finally:
                    if channel:
                        try:
                            channel.close()
                        except Exception:
                            pass
                time.sleep(2)

        threading.Thread(target=telemetry_worker, daemon=True, name="CitadelVitals").start()

    # ── Logging ───────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        end = self._log_buffer.get_end_iter()
        self._log_buffer.insert(end, f"[{ts}] {msg}\n")
        mark = self._log_buffer.create_mark(None, self._log_buffer.get_end_iter(), False)
        self._log_view.scroll_mark_onscreen(mark)
