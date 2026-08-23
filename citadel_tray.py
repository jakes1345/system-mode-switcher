#!/usr/bin/env python3
import os
import sys
import threading
import grpc

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk
from gi.repository import AyatanaAppIndicator3 as appindicator

# Add local paths so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'services/hub'))

import citadel_pb2
import citadel_pb2_grpc
from switcher.config import load_config
from gi.repository import GLib

class CitadelTrayApp:
    def __init__(self):
        self.config = load_config()
        self.active_profile = ""
        
        # Connect to gRPC Daemon
        channel = grpc.insecure_channel('localhost:50051')
        self.stub = citadel_pb2_grpc.CitadelServiceStub(channel)

        # Use absolute path directly — bypasses AppIndicator's theme-name cache
        # which stubbornly serves stale icons even after theme cache rebuilds.
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets/icon.png"))
        self.indicator = appindicator.Indicator.new(
            "obsidian-citadel-tray",
            icon_path,
            appindicator.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.menu_items = {} # Store refs to update text
        self.indicator.set_menu(self.build_menu())
        
        # Start background update loop
        GLib.timeout_add_seconds(2, self.update_status)

    def build_menu(self):
        menu = Gtk.Menu()

        # Title Item
        title = Gtk.MenuItem(label="Obsidian Citadel OS")
        title.set_sensitive(False)
        menu.append(title)
        
        menu.append(Gtk.SeparatorMenuItem())

        # Profiles
        for name, profile in self.config.profiles.items():
            item = Gtk.MenuItem(label=f"Activate: {name}")
            item.connect("activate", self.on_profile_click, name)
            self.menu_items[name] = item
            menu.append(item)

        menu.append(Gtk.SeparatorMenuItem())
        
        # Open Dashboard (optional later)
        dashboard_item = Gtk.MenuItem(label="Open Dashboard...")
        dashboard_item.connect("activate", self.on_dashboard_click)
        menu.append(dashboard_item)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", Gtk.main_quit)
        menu.append(quit_item)

        menu.show_all()
        return menu

    def set_profile_async(self, profile_name):
        try:
            req = citadel_pb2.SetProfileRequest(profile_name=profile_name)
            resp = self.stub.SetProfile(req)
            print(f"Switched to {profile_name}: {resp.message}")
        except Exception as e:
            print(f"Error switching profile: {e}")

    def on_profile_click(self, widget, profile_name):
        # Fire gRPC call in background thread to avoid freezing GTK
        threading.Thread(target=self.set_profile_async, args=(profile_name,), daemon=True).start()
        
    def on_dashboard_click(self, widget):
        # Launch main UI in background
        os.system("python3 main.py &")

    def update_status(self):
        try:
            req = citadel_pb2.StateRequest()
            resp = self.stub.GetCurrentState(req)
            new_profile = resp.active_profile
            
            if new_profile != self.active_profile:
                self.active_profile = new_profile
                
                # Update UI elements
                for name, item in self.menu_items.items():
                    if name == self.active_profile:
                        item.set_label(f"✓ Active: {name}")
                    else:
                        item.set_label(f"Switch to {name}")
                        
        except Exception:
            pass
            
        return True # Keep polling

if __name__ == "__main__":
    app = CitadelTrayApp()
    Gtk.main()
