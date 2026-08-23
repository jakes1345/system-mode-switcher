"""Right pane — services, processes, and system tweaks."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from switcher.backend import (
    GPU_VENDOR,
    get_compositor_unredirect,
    get_gpu_performance_mode,
    get_swappiness,
    is_process_running,
    is_service_active,
)
from switcher.config import Config, TweakConfig


class ServiceRow(Gtk.Box):
    """A single service/process row with name, description, status dot, and switch."""

    def __init__(self, key: str, display: str, description: str):
        super().__init__(spacing=8)
        self.key = key
        self.get_style_context().add_class("service-row")
        self.set_margin_start(4)
        self.set_margin_end(4)

        # Name + desc
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.name_label = Gtk.Label(label=display, xalign=0)
        self.name_label.get_style_context().add_class("service-name")
        vbox.pack_start(self.name_label, False, False, 0)

        self.desc_label = Gtk.Label(label=description, xalign=0)
        self.desc_label.get_style_context().add_class("service-desc")
        vbox.pack_start(self.desc_label, False, False, 0)
        self.pack_start(vbox, True, True, 0)

        # Status dot
        self.status_dot = Gtk.Label(label="\u25cf")  # filled circle
        self.status_dot.get_style_context().add_class("status-dot")
        self.status_dot.get_style_context().add_class("off")
        self.status_dot.set_valign(Gtk.Align.CENTER)
        self.pack_start(self.status_dot, False, False, 0)

        # Switch
        self.switch = Gtk.Switch()
        self.switch.set_valign(Gtk.Align.CENTER)
        self.pack_start(self.switch, False, False, 0)

    def set_status(self, active: bool) -> None:
        ctx = self.status_dot.get_style_context()
        ctx.remove_class("on")
        ctx.remove_class("off")
        ctx.add_class("on" if active else "off")

    def matches_search(self, query: str) -> bool:
        if not query:
            return True
        q = query.lower()
        return (
            q in self.name_label.get_text().lower()
            or q in self.desc_label.get_text().lower()
            or q in self.key.lower()
        )


class ServicePanel(Gtk.Box):
    """Right pane: search, services, processes, tweaks."""

    def __init__(self, config: Config):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.get_style_context().add_class("panel-bg")

        self._config = config
        self.service_rows: dict[str, ServiceRow] = {}
        self.process_rows: dict[str, ServiceRow] = {}

        # Search
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search services...")
        self.search_entry.get_style_context().add_class("search-entry")
        self.search_entry.set_margin_top(12)
        self.search_entry.set_margin_start(12)
        self.search_entry.set_margin_end(12)
        self.search_entry.connect("search-changed", self._on_search)
        self.pack_start(self.search_entry, False, False, 0)

        # Scrollable content
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        inner.set_margin_top(8)
        inner.set_margin_bottom(8)
        inner.set_margin_start(12)
        inner.set_margin_end(12)

        # Services section
        categories = {}
        for svc in config.services:
            cat = getattr(svc, "category", "System")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(svc)

        for cat in sorted(categories.keys()):
            svc_label = Gtk.Label(label=f"{cat.upper()} SERVICES", xalign=0)
            svc_label.get_style_context().add_class("section-label")
            svc_label.set_margin_top(8)
            svc_label.set_margin_bottom(4)
            inner.pack_start(svc_label, False, False, 0)

            for svc in categories[cat]:
                row = ServiceRow(svc.name, svc.display, svc.description)
                self.service_rows[svc.name] = row
                inner.pack_start(row, False, False, 0)

        # Processes section
        if config.processes:
            inner.pack_start(Gtk.Separator(), False, False, 8)
            proc_label = Gtk.Label(label="PROCESSES", xalign=0)
            proc_label.get_style_context().add_class("section-label")
            proc_label.set_margin_bottom(4)
            inner.pack_start(proc_label, False, False, 0)

            for proc in config.processes:
                row = ServiceRow(proc.id, proc.display, proc.description)
                self.process_rows[proc.id] = row
                inner.pack_start(row, False, False, 0)

        # ── Hardware Cockpit ────────────────────────────────────────────────
        inner.pack_start(Gtk.Separator(), False, False, 12)
        hw_label = Gtk.Label(label="HARDWARE COCKPIT", xalign=0)
        hw_label.get_style_context().add_class("section-label")
        hw_label.set_margin_bottom(8)
        inner.pack_start(hw_label, False, False, 0)

        # CPU Governor
        self.gov_combo = self._add_tweak_combo(inner, "CPU Frequency Governor", [
            ("performance", "High Performance"),
            ("powersave", "Power Efficient")
        ], "performance")

        # GPU Power Limit (NVIDIA Only)
        if GPU_VENDOR == "nvidia":
            self.pl_scale = self._add_tweak_scale(inner, "NVIDIA Power Limit (W)", 125, 175, 175)

        # THP Mode
        self.thp_combo = self._add_tweak_combo(inner, "Transparent Hugepages", [
            ("always", "Always (AI Focus)"),
            ("madvise", "Madvise (Balanced)"),
            ("never", "Disabled")
        ], "madvise")

        # ── Legacy System Tweaks ───────────────────────────────────────────
        inner.pack_start(Gtk.Separator(), False, False, 12)
        sw_label = Gtk.Label(label="SYSTEM CORE TWEAKS", xalign=0)
        sw_label.get_style_context().add_class("section-label")
        sw_label.set_margin_bottom(8)
        inner.pack_start(sw_label, False, False, 0)

        # Probed values are set asynchronously after window draws (see refresh_switches).
        # Initial values are safe defaults so UI renders instantly.
        self.swappiness_scale = self._add_tweak_scale(inner, "Kernel Swappiness", 0, 100, 60)

        self.unredirect_switch = self._add_tweak_switch(inner, "Unredirect Fullscreen (Low Latency)", False)

        gpu_text = "NVIDIA Adaptive Perf" if GPU_VENDOR == "nvidia" else "AMD Performance Mode"
        self.gpu_perf_switch = self._add_tweak_switch(inner, gpu_text, False)

        inner.pack_start(Gtk.Separator(), False, False, 12)

        scroll.add(inner)
        self.pack_start(scroll, True, True, 0)

    def _add_tweak_row(self, container, label_text):
        row = Gtk.Box(spacing=10)
        row.get_style_context().add_class("tweak-row")
        lbl = Gtk.Label(label=label_text, xalign=0)
        lbl.get_style_context().add_class("tweak-label")
        row.pack_start(lbl, True, True, 0)
        container.pack_start(row, False, False, 0)
        return row

    def _add_tweak_switch(self, container, label, active):
        row = self._add_tweak_row(container, label)
        sw = Gtk.Switch(active=active, valign=Gtk.Align.CENTER)
        row.pack_start(sw, False, False, 0)
        return sw

    def _add_tweak_scale(self, container, label, low, high, value):
        row = self._add_tweak_row(container, label)
        sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, low, high, 5)
        sc.set_size_request(150, -1)
        sc.set_value(value)
        row.pack_start(sc, False, False, 0)
        return sc

    def _add_tweak_combo(self, container, label, options, active_id):
        row = self._add_tweak_row(container, label)
        cb = Gtk.ComboBoxText()
        for id_val, text in options:
            cb.append(id_val, text)
        cb.set_active_id(active_id)
        row.pack_start(cb, False, False, 0)
        return cb

    def refresh_status(self) -> None:
        """Update status dots from live system state in background thread."""
        services = list(self.service_rows.keys())
        processes = [
            (p.id, p.grep)
            for p in self._config.processes
            if p.id in self.process_rows
        ]

        def _worker():
            svc_status = {name: is_service_active(name) for name in services}
            proc_status = {pid: is_process_running(grep) for pid, grep in processes}
            def _apply():
                for name, active in svc_status.items():
                    if name in self.service_rows:
                        self.service_rows[name].set_status(active)
                for pid, active in proc_status.items():
                    if pid in self.process_rows:
                        self.process_rows[pid].set_status(active)
                return False
            GLib.idle_add(_apply)

        threading.Thread(target=_worker, daemon=True, name="StatusRefreshWorker").start()

    def refresh_switches(self, on_done=None) -> None:
        """Probe live system state in a background thread, then update UI on the main loop.

        Runs subprocess calls (systemctl, pgrep, gsettings, nvidia-settings) off the
        main thread so the window paints instantly instead of blocking 1-3s on startup.
        """
        services = list(self.service_rows.keys())
        processes = [
            (p.id, p.grep)
            for p in self._config.processes
            if p.id in self.process_rows
        ]

        def _probe():
            results = {
                "services": {name: is_service_active(name) for name in services},
                "processes": {pid: is_process_running(grep) for pid, grep in processes},
                "swappiness": get_swappiness(),
                "unredirect": get_compositor_unredirect(),
                "gpu_perf": get_gpu_performance_mode(),
            }
            GLib.idle_add(self._apply_probe_results, results, on_done)

        threading.Thread(target=_probe, daemon=True, name="ProbeWorker").start()

    def _apply_probe_results(self, results: dict, on_done=None) -> bool:
        for svc_name, active in results["services"].items():
            row = self.service_rows.get(svc_name)
            if row:
                row.switch.set_active(active)
                row.set_status(active)

        for proc_id, active in results["processes"].items():
            row = self.process_rows.get(proc_id)
            if row:
                row.switch.set_active(active)
                row.set_status(active)

        self.swappiness_scale.set_value(results["swappiness"])
        self.unredirect_switch.set_active(results["unredirect"])
        if results["gpu_perf"] is not None:
            self.gpu_perf_switch.set_active(results["gpu_perf"])
        if callable(on_done):
            on_done()
        return False

    def apply_profile(self, services: dict[str, bool], processes: dict[str, bool],
                      tweaks: TweakConfig) -> None:
        """Set switches to match a profile. Does NOT apply to system."""
        for svc_name, desired in services.items():
            if svc_name in self.service_rows:
                self.service_rows[svc_name].switch.set_active(desired)

        for proc_id, desired in processes.items():
            if proc_id in self.process_rows:
                self.process_rows[proc_id].switch.set_active(desired)

        self.swappiness_scale.set_value(tweaks.swappiness)
        self.unredirect_switch.set_active(tweaks.compositor_unredirect)
        self.gpu_perf_switch.set_active(tweaks.gpu_performance)
        self.gov_combo.set_active_id(tweaks.cpu_governor)
        
        if hasattr(self, "pl_scale") and tweaks.gpu_power_limit:
            self.pl_scale.set_value(tweaks.gpu_power_limit)
        
        self.thp_combo.set_active_id(tweaks.thp_mode)

    def collect_desired_state(self) -> dict:
        """Snapshot all switch states for thread-safe apply."""
        return {
            "services": {
                name: row.switch.get_active()
                for name, row in self.service_rows.items()
            },
            "processes": {
                pid: row.switch.get_active()
                for pid, row in self.process_rows.items()
            },
            "swappiness": int(self.swappiness_scale.get_value()),
            "unredirect": self.unredirect_switch.get_active(),
            "gpu_perf": self.gpu_perf_switch.get_active(),
            "cpu_gov": self.gov_combo.get_active_id(),
            "gpu_pl": int(self.pl_scale.get_value()) if hasattr(self, "pl_scale") else None,
            "thp": self.thp_combo.get_active_id(),
        }

    def _on_search(self, entry: Gtk.SearchEntry) -> None:
        query = entry.get_text()
        for row in self.service_rows.values():
            row.set_visible(row.matches_search(query))
        for row in self.process_rows.values():
            row.set_visible(row.matches_search(query))
