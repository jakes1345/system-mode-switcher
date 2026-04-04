"""Right pane — services, processes, and system tweaks."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from switcher.backend import (
    GPU_VENDOR,
    get_compositor_unredirect,
    get_gpu_performance_mode,
    get_swappiness,
    is_process_running,
    is_service_active,
)
from switcher.config import Config


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
        svc_label = Gtk.Label(label="SERVICES", xalign=0)
        svc_label.get_style_context().add_class("section-label")
        svc_label.set_margin_top(4)
        svc_label.set_margin_bottom(4)
        inner.pack_start(svc_label, False, False, 0)

        for svc in config.services:
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

        # Tweaks section
        inner.pack_start(Gtk.Separator(), False, False, 8)
        tweak_label = Gtk.Label(label="SYSTEM TWEAKS", xalign=0)
        tweak_label.get_style_context().add_class("section-label")
        tweak_label.set_margin_bottom(4)
        inner.pack_start(tweak_label, False, False, 0)

        # Swappiness
        swap_row = Gtk.Box(spacing=10)
        swap_row.get_style_context().add_class("tweak-row")
        swap_lbl = Gtk.Label(label="vm.swappiness", xalign=0)
        swap_lbl.get_style_context().add_class("tweak-label")
        swap_row.pack_start(swap_lbl, True, True, 0)
        self.swappiness_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 1, 100, 5
        )
        self.swappiness_scale.set_size_request(200, -1)
        self.swappiness_scale.set_value(get_swappiness())
        swap_row.pack_start(self.swappiness_scale, False, False, 0)
        inner.pack_start(swap_row, False, False, 0)

        # Compositor unredirect
        comp_row = Gtk.Box(spacing=10)
        comp_row.get_style_context().add_class("tweak-row")
        comp_lbl = Gtk.Label(
            label="Unredirect fullscreen windows (less input lag)", xalign=0
        )
        comp_lbl.get_style_context().add_class("tweak-label")
        comp_row.pack_start(comp_lbl, True, True, 0)
        self.unredirect_switch = Gtk.Switch()
        self.unredirect_switch.set_active(get_compositor_unredirect())
        self.unredirect_switch.set_valign(Gtk.Align.CENTER)
        comp_row.pack_start(self.unredirect_switch, False, False, 0)
        inner.pack_start(comp_row, False, False, 0)

        # GPU performance
        gpu_labels = {
            "nvidia": "NVIDIA Prefer Max Performance",
            "amd": "AMD GPU Performance Mode (LACT)",
        }
        gpu_text = gpu_labels.get(GPU_VENDOR, "GPU Performance Mode (no supported GPU)")
        gpu_row = Gtk.Box(spacing=10)
        gpu_row.get_style_context().add_class("tweak-row")
        gpu_lbl = Gtk.Label(label=gpu_text, xalign=0)
        gpu_lbl.get_style_context().add_class("tweak-label")
        gpu_row.pack_start(gpu_lbl, True, True, 0)
        self.gpu_perf_switch = Gtk.Switch()
        self.gpu_perf_switch.set_valign(Gtk.Align.CENTER)
        if GPU_VENDOR == "unknown":
            self.gpu_perf_switch.set_sensitive(False)
        gpu_row.pack_start(self.gpu_perf_switch, False, False, 0)
        inner.pack_start(gpu_row, False, False, 0)

        scroll.add(inner)
        self.pack_start(scroll, True, True, 0)

    def refresh_status(self) -> None:
        """Update status dots from live system state. Does NOT touch switches."""
        for svc_name, row in self.service_rows.items():
            row.set_status(is_service_active(svc_name))

        for proc_id, row in self.process_rows.items():
            proc = next(
                (p for p in self._config.processes if p.id == proc_id), None
            )
            if proc:
                row.set_status(is_process_running(proc.grep))

    def refresh_switches(self) -> None:
        """Update switches AND status from live state. Used on initial load."""
        for svc_name, row in self.service_rows.items():
            active = is_service_active(svc_name)
            row.switch.set_active(active)
            row.set_status(active)

        for proc_id, row in self.process_rows.items():
            proc = next(
                (p for p in self._config.processes if p.id == proc_id), None
            )
            if proc:
                active = is_process_running(proc.grep)
                row.switch.set_active(active)
                row.set_status(active)

        self.swappiness_scale.set_value(get_swappiness())
        self.unredirect_switch.set_active(get_compositor_unredirect())
        gpu_mode = get_gpu_performance_mode()
        if gpu_mode is not None:
            self.gpu_perf_switch.set_active(gpu_mode)

    def apply_profile(self, services: dict[str, bool], processes: dict[str, bool],
                      tweaks) -> None:
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
        }

    def _on_search(self, entry: Gtk.SearchEntry) -> None:
        query = entry.get_text()
        for row in self.service_rows.values():
            row.set_visible(row.matches_search(query))
        for row in self.process_rows.values():
            row.set_visible(row.matches_search(query))
