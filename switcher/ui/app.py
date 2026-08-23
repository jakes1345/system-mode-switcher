"""Gtk.Application — single-instance app with CSS and tray icon."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator3
    HAS_INDICATOR = True
except (ValueError, ImportError):
    try:
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import AppIndicator3
        HAS_INDICATOR = True
    except (ValueError, ImportError):
        HAS_INDICATOR = False

from gi.repository import Gdk, Gio, Gtk

from switcher.config import load_config
from switcher.ui.css import CSS
from switcher.ui.dialogs import show_error_dialog
from switcher.ui.window import SwitcherWindow


class SwitcherApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.obsidian.citadel",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self._window: SwitcherWindow | None = None

    def do_startup(self):
        Gtk.Application.do_startup(self)

        # Force dark theme base
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", True)

        # Load CSS
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def do_activate(self):
        if self._window:
            self._window.present()
            return

        # Load config
        config = load_config()
        if config.load_error:
            show_error_dialog(None, "Configuration Error", config.load_error)

        self._window = SwitcherWindow(self, config)
        self._window.show_all()
        self._window._progress.hide()  # hidden by default

        # System tray
        self._setup_tray()

    def _setup_tray(self) -> None:
        if not HAS_INDICATOR or not self._window:
            return

        indicator = AppIndicator3.Indicator.new(
            "obsidian-citadel",
            "preferences-system",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        menu = Gtk.Menu()

        for name in self._window._config.profiles:
            item = Gtk.MenuItem(label=name)
            item.connect(
                "activate",
                lambda _w, n=name: self._tray_apply(n),
            )
            menu.append(item)

        menu.append(Gtk.SeparatorMenuItem())

        show_item = Gtk.MenuItem(label="Show Window")
        show_item.connect("activate", lambda _: self._window.present())
        menu.append(show_item)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _: self.quit())
        menu.append(quit_item)

        menu.show_all()
        indicator.set_menu(menu)

    def _tray_apply(self, profile_name: str) -> None:
        if self._window:
            self._window._on_profile_select(profile_name)
            self._window.present()
