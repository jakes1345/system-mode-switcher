"""Left sidebar — profile cards with selection and context menu."""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk

from switcher.config import ProfileConfig


class ProfileCard(Gtk.EventBox):
    """A clickable profile card with colored border."""

    def __init__(
        self,
        profile: ProfileConfig,
        on_select: Callable[[str], None],
        on_delete: Callable[[str], None] | None,
    ):
        super().__init__()
        self.profile_name = profile.name
        self._on_select = on_select
        self._on_delete = on_delete
        self._color = profile.color

        self._frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._frame.get_style_context().add_class("profile-card")
        self._frame.set_margin_start(0)
        self._frame.set_margin_end(8)
        self._frame.set_margin_top(1)
        self._frame.set_margin_bottom(1)

        # Always show profile color as left border
        self._base_provider = Gtk.CssProvider()
        self._base_provider.load_from_data(
            f".profile-card {{ border-left-color: {profile.color}; }}".encode()
        )
        self._frame.get_style_context().add_provider(
            self._base_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        name_lbl = Gtk.Label(label=profile.name, xalign=0)
        name_lbl.get_style_context().add_class("profile-card-name")
        self._frame.pack_start(name_lbl, False, False, 0)

        if profile.description:
            desc_lbl = Gtk.Label(label=profile.description, xalign=0, wrap=True)
            desc_lbl.set_max_width_chars(22)
            desc_lbl.get_style_context().add_class("profile-card-desc")
            self._frame.pack_start(desc_lbl, False, False, 0)

        self.add(self._frame)

        self.connect("button-press-event", self._on_click)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)

    def _on_click(self, _widget, event: Gdk.EventButton):
        if event.button == 1:  # Left click
            self._on_select(self.profile_name)
        elif event.button == 3 and self._on_delete:  # Right click
            menu = Gtk.Menu()
            delete_item = Gtk.MenuItem(label=f"Delete '{self.profile_name}'")
            delete_item.connect("activate", lambda _: self._on_delete(self.profile_name))
            menu.append(delete_item)
            menu.show_all()
            menu.popup_at_pointer(event)

    def set_active(self, active: bool) -> None:
        ctx = self._frame.get_style_context()
        if active:
            ctx.add_class("active")
            # Active card: thicker color stripe + tinted background
            provider = Gtk.CssProvider()
            provider.load_from_data((
                f".profile-card.active {{"
                f"  border-left: 4px solid {self._color};"
                f"  background: shade({self._color}, 0.15);"
                f"  transition: all 0.2s ease-in-out;"
                f"}}"
            ).encode())
            ctx.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2)
        else:
            ctx.remove_class("active")


class ProfileSidebar(Gtk.Box):
    """Sidebar containing profile cards and save button."""

    def __init__(
        self,
        profiles: dict[str, ProfileConfig],
        on_select: Callable[[str], None],
        on_delete: Callable[[str], None],
        on_save: Callable[[], None],
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.get_style_context().add_class("sidebar")
        self.set_size_request(220, -1)

        self._on_select = on_select
        self._on_delete = on_delete
        self._cards: dict[str, ProfileCard] = {}

        # Header
        header = Gtk.Label(label="PROFILES", xalign=0)
        header.get_style_context().add_class("sidebar-title")
        header.set_margin_top(16)
        header.set_margin_start(16)
        header.set_margin_bottom(8)
        self.pack_start(header, False, False, 0)

        # Scrollable card list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        self._card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._card_box.set_margin_top(4)
        scroll.add(self._card_box)
        self.pack_start(scroll, True, True, 0)

        # Add profile cards
        for name, profile in profiles.items():
            self.add_profile_card(profile)

        # Save button at bottom
        save_btn = Gtk.Button(label="+ Save Current as Profile")
        save_btn.get_style_context().add_class("save-profile-btn")
        save_btn.set_margin_start(8)
        save_btn.set_margin_end(8)
        save_btn.set_margin_top(8)
        save_btn.set_margin_bottom(12)
        save_btn.connect("clicked", lambda _: on_save())
        self.pack_start(save_btn, False, False, 0)

    def add_profile_card(self, profile: ProfileConfig) -> None:
        on_del = self._on_delete if not profile.builtin else None
        card = ProfileCard(profile, self._on_select, on_del)
        self._cards[profile.name] = card
        self._card_box.pack_start(card, False, False, 0)
        card.show_all()

    def remove_profile_card(self, name: str) -> None:
        card = self._cards.pop(name, None)
        if card:
            self._card_box.remove(card)

    def set_active_profile(self, name: str | None) -> None:
        for card_name, card in self._cards.items():
            card.set_active(card_name == name)
