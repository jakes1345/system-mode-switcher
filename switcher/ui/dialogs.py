"""Dialog helpers — save profile, confirm apply."""

from __future__ import annotations

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk


def save_profile_dialog(parent: Gtk.Window) -> tuple[str, str] | None:
    """Show save-profile dialog. Returns (name, color) or None if cancelled."""
    dialog = Gtk.Dialog(
        title="Save Custom Profile",
        parent=parent,
        flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
    )
    dialog.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Save", Gtk.ResponseType.OK)

    box = dialog.get_content_area()
    box.set_margin_top(16)
    box.set_margin_bottom(16)
    box.set_margin_start(16)
    box.set_margin_end(16)
    box.set_spacing(10)

    # Name
    name_label = Gtk.Label(label="Profile name:", xalign=0)
    name_label.get_style_context().add_class("dialog-label")
    box.pack_start(name_label, False, False, 0)

    name_entry = Gtk.Entry()
    name_entry.set_placeholder_text("My Custom Profile")
    name_entry.connect("activate", lambda _e: dialog.response(Gtk.ResponseType.OK))
    box.pack_start(name_entry, False, False, 0)

    # Color
    color_label = Gtk.Label(label="Accent color:", xalign=0)
    color_label.get_style_context().add_class("dialog-label")
    box.pack_start(color_label, False, False, 0)

    color_btn = Gtk.ColorButton()
    rgba = Gdk.RGBA()
    rgba.parse("#4fc3f7")
    color_btn.set_rgba(rgba)
    box.pack_start(color_btn, False, False, 0)

    dialog.show_all()
    response = dialog.run()
    name = name_entry.get_text().strip()
    rgba = color_btn.get_rgba()
    color = "#{:02x}{:02x}{:02x}".format(
        int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255)
    )
    dialog.destroy()

    if response != Gtk.ResponseType.OK or not name:
        return None
    return name, color


def confirm_apply_dialog(parent: Gtk.Window, changes: list[str]) -> bool:
    """Show confirmation dialog listing changes. Returns True if user confirms."""
    if not changes:
        return False

    dialog = Gtk.MessageDialog(
        parent=parent,
        flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        text=f"Apply {len(changes)} change(s)?",
    )
    dialog.format_secondary_text("\n".join(changes))
    response = dialog.run()
    dialog.destroy()
    return response == Gtk.ResponseType.OK


def confirm_delete_dialog(parent: Gtk.Window, profile_name: str) -> bool:
    """Confirm deletion of a custom profile."""
    dialog = Gtk.MessageDialog(
        parent=parent,
        flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        message_type=Gtk.MessageType.WARNING,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        text=f"Delete profile '{profile_name}'?",
    )
    dialog.format_secondary_text("This cannot be undone.")
    response = dialog.run()
    dialog.destroy()
    return response == Gtk.ResponseType.OK


def show_error_dialog(parent: Gtk.Window | None, title: str, message: str) -> None:
    """Show an error dialog."""
    dialog = Gtk.MessageDialog(
        parent=parent,
        flags=Gtk.DialogFlags.MODAL,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=title,
    )
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()
