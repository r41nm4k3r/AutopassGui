import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import serial
import serial.tools.list_ports
import time
import json
import os
import threading
import asyncio
from pathlib import Path


class ArduinoControlApp(toga.App):
    """Arduino Trigger Control Application using Toga/Beeware"""
    
    CONFIG_FILE = "settings.json"
    
    def __init__(self):
        super().__init__(
            'Autopass GUI',
            'com.nnyx.arduinocontrol',
            icon='resources/autopass-gui.png'
        )
        self.ser = None
        self.config = self.load_config()
        self.button_labels = {
            **self.default_settings()["labels"],
            **self.config.get("labels", {})
        }
        self.is_locked = self.config.get("lock", {}).get("enabled", False)
        self.last_activity = time.time()
        self.auto_lock_timer = None
        self.start_auto_lock_timer()
        
        # Store original commands for restoration
        self.original_commands = []
    
    def default_settings(self):
        """Return default configuration settings"""
        return {
            "labels": {
                "password1": "Send Password 1",
                "password2": "Send Password 2",
                "password3": "Send Password 3",
                "password4": "Send Password 4"
            },
            "theme": "dark",
            "lock": {
                "enabled": False,
                "pin": "",
                "auto_lock_timeout": 0  # minutes, 0 = disabled
            }
        }
    
    def load_config(self):
        """Load configuration from JSON file"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    return {**self.default_settings(), **data}
            except Exception:
                return self.default_settings().copy()
        return self.default_settings().copy()
    
    def save_config(self):
        """Save configuration to JSON file"""
        with open(self.CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def list_serial_ports(self):
        """List available serial ports"""
        ports = [p.device for p in serial.tools.list_ports.comports()]
        return ports if ports else ["No ports found"]
    
    def startup(self):
        """Construct and show the Toga application."""
        # === Create Menu ===
        self.create_menu()
        
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=10))
        
        # === Theme Toggle Button (Top Right) ===
        theme_box = toga.Box(style=Pack(direction=ROW, margin=5))
        spacer = toga.Box(style=Pack(flex=1))  # Push buttons to the right
        theme_box.add(spacer)
        
        # Lock toggle button
        self.lock_btn = toga.Button(
            '🔒' if self.is_locked else '🔓',
            on_press=self.toggle_lock,
            style=Pack(width=50, margin_right=5)
        )
        theme_box.add(self.lock_btn)
        
        self.theme_btn = toga.Button(
            '🌙' if self.config.get("theme", "dark") == "light" else '☀️',
            on_press=self.toggle_theme,
            style=Pack(width=50)
        )
        theme_box.add(self.theme_btn)
        main_box.add(theme_box)
        
        try:
            logo_image = toga.Image("resources/autopass-gui.png")
        except Exception:
            # fallback if logo not found
            logo_image = toga.Image("resources/autopass-gui.png")
        # Add the image as a logo at the top
                # Create a box to center the logo
        logo_box = toga.Box(style=Pack(direction=ROW))
        logo_widget = toga.ImageView(logo_image, style=Pack(width=128, height=128, margin_bottom=20))
        
        # Add spacers to center the image
        logo_box.add(toga.Box(style=Pack(flex=1)))
        logo_box.add(logo_widget)
        logo_box.add(toga.Box(style=Pack(flex=1)))

        # Add your other widgets (example)
        label = toga.Label("Welcome to AutoPass!", style=Pack(text_align='center', margin=10))

        # Add widgets to the box
        main_box.add(logo_box)
        main_box.add(label)

        # # === Logo Section ===
        # logo_label = toga.Label(
        #     '🔑',
        #     style=Pack(margin=5, font_size=36, text_align='center')
        # )
        #main_box.add(logo_label)
        
        # === Title Section ===
        title_label = toga.Label(
            'Arduino Trigger Control',
            style=Pack(margin=5, font_size=20, font_weight='bold', text_align='center')
        )
        main_box.add(title_label)
        
        subtitle_label = toga.Label(
            '• Autotype Credentials via Arduino •',
            style=Pack(margin=20, font_size=12, text_align='center')
        )
        main_box.add(subtitle_label)
        
        # === Port Selection Section ===
        port_box = toga.Box(style=Pack(direction=ROW, margin=10))
        
        port_label = toga.Label(
            'Select Port:',
            style=Pack(margin_right=10, width=100)
        )
        port_box.add(port_label)
        
        self.port_selection = toga.Selection(
            items=self.list_serial_ports(),
            style=Pack(flex=1, margin_right=10)
        )
        port_box.add(self.port_selection)
        
        refresh_btn = toga.Button(
            '↻ Refresh',
            on_press=self.refresh_ports,
            style=Pack(width=100)
        )
        port_box.add(refresh_btn)
        
        main_box.add(port_box)
        
        # === Connect / Disconnect Buttons ===
        conn_box = toga.Box(style=Pack(direction=ROW, margin=10))
        
        self.connect_btn = toga.Button(
            '🔌 Connect',
            on_press=self.connect_arduino,
            style=Pack(flex=1, margin_right=10)
        )
        conn_box.add(self.connect_btn)
        
        self.disconnect_btn = toga.Button(
            '❌ Disconnect',
            on_press=self.disconnect_arduino,
            enabled=False,
            style=Pack(flex=1)
        )
        conn_box.add(self.disconnect_btn)
        
        main_box.add(conn_box)
        
        # === Command Buttons Grid ===
        self.buttons = {}
        
        # Row 1
        row1_box = toga.Box(style=Pack(direction=ROW, margin=5))
        self.create_button_row(row1_box, "password1")
        self.create_button_row(row1_box, "password2")
        main_box.add(row1_box)
        
        # Row 2
        row2_box = toga.Box(style=Pack(direction=ROW, margin=5))
        self.create_button_row(row2_box, "password3")
        self.create_button_row(row2_box, "password4")
        main_box.add(row2_box)
        
        # === Custom Command Section ===
        custom_box = toga.Box(style=Pack(direction=COLUMN, margin=10))
        
        self.custom_entry = toga.TextInput(
            placeholder='Type custom command...',
            style=Pack(margin=5, flex=1)
        )
        custom_box.add(self.custom_entry)
        
        send_custom_btn = toga.Button(
            'Send Custom Command',
            on_press=self.send_custom_command,
            style=Pack(margin=5)
        )
        custom_box.add(send_custom_btn)
        
        main_box.add(custom_box)
        
        # === Status Label ===
        self.status_label = toga.Label(
            'Not connected',
            style=Pack(margin=10, text_align='center', color='#FF0000')
        )
        main_box.add(self.status_label)
        
        # === Log Label ===
        self.log_label = toga.Label(
            '',
            style=Pack(margin=5, text_align='center', color='#808080')
        )
        main_box.add(self.log_label)
        
        # === Footer ===
        footer_label = toga.Label(
            '© 2025 NnyX Technologies',
            style=Pack(margin=10, text_align='center', font_size=10)
        )
        main_box.add(footer_label)
        
        # === Main Window ===
        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_content = main_box  # Store reference to main content
        
        # Create lockscreen overlay
        self.lockscreen_box = self.create_lockscreen()
        
        # Show appropriate content based on lock state
        self.update_ui_visibility()
        
        self.apply_theme()
        self.main_window.show()
        
        # Store original commands for restoration
        self.original_commands = []
    
    def create_lockscreen(self):
        """Create the lockscreen overlay UI"""
        lockscreen = toga.Box(style=Pack(direction=COLUMN, margin=20))
        
        # Centered content
        center_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        
        # Lock icon
        lock_icon_box = toga.Box(style=Pack(direction=ROW))
        lock_icon_box.add(toga.Box(style=Pack(flex=1)))  # Left spacer
        lock_icon = toga.Label(
            '🔒',
            style=Pack(font_size=72, text_align='center', margin_bottom=20)
        )
        lock_icon_box.add(lock_icon)
        lock_icon_box.add(toga.Box(style=Pack(flex=1)))  # Right spacer
        center_box.add(lock_icon_box)
        
        # Title
        title = toga.Label(
            'Autopass GUI Locked',
            style=Pack(font_size=24, font_weight='bold', text_align='center', margin_bottom=10)
        )
        center_box.add(title)
        
        # PIN input
        pin_box = toga.Box(style=Pack(direction=COLUMN, margin=20))
        pin_label = toga.Label(
            'Enter PIN to unlock:',
            style=Pack(margin_bottom=10, text_align='center')
        )
        pin_box.add(pin_label)
        
        # Center the input and button horizontally
        input_button_box = toga.Box(style=Pack(direction=ROW))
        input_button_box.add(toga.Box(style=Pack(flex=1)))  # Left spacer
        
        input_container = toga.Box(style=Pack(direction=COLUMN))
        self.pin_input = toga.PasswordInput(
            placeholder='Enter PIN',
            style=Pack(margin_bottom=10, width=200)
        )
        input_container.add(self.pin_input)
        
        unlock_btn = toga.Button(
            'Unlock',
            on_press=self.attempt_unlock,
            style=Pack(width=200)
        )
        input_container.add(unlock_btn)
        
        input_button_box.add(input_container)
        input_button_box.add(toga.Box(style=Pack(flex=1)))  # Right spacer
        
        pin_box.add(input_button_box)
        
        self.unlock_status = toga.Label(
            '',
            style=Pack(text_align='center', margin_top=10, color='#FF0000')
        )
        pin_box.add(self.unlock_status)
        
        center_box.add(pin_box)
        
        # Add spacers to center vertically
        lockscreen.add(toga.Box(style=Pack(flex=1)))
        lockscreen.add(center_box)
        lockscreen.add(toga.Box(style=Pack(flex=1)))
        
        return lockscreen
    
    def update_ui_visibility(self):
        """Update which UI is visible based on lock state"""
        if self.is_locked:
            self.main_window.content = self.lockscreen_box
            self.main_window.title = f"{self.formal_name} - LOCKED"
            # Disable all commands when locked
            self.disable_commands()
        else:
            self.main_window.content = self.main_content
            self.main_window.title = self.formal_name
            # Enable all commands when unlocked
            self.enable_commands()
    
    def disable_commands(self):
        """Disable all menu commands when locked"""
        try:
            # Try to hide the toolbar/menu widget
            if hasattr(self.main_window, '_impl') and hasattr(self.main_window._impl, 'toolbar'):
                self.main_window._impl.toolbar.set_visible(False)
            elif hasattr(self.main_window, 'toolbar'):
                self.main_window.toolbar.visible = False
            
            # Hide GTK menu bar aggressively
            self.hide_gtk_menubar()
            
            # Disable all commands
            for command in self.commands:
                command.enabled = False
            
            # Additional GTK menubar hiding - try to disable the menubar completely
            try:
                import gi
                gi.require_version('Gtk', '3.0')
                from gi.repository import Gtk
                
                gtk_window = self.main_window._impl.native
                
                # Try to remove menubar from window
                if hasattr(gtk_window, 'get_menubar'):
                    menubar = gtk_window.get_menubar()
                    if menubar:
                        # Try to make it insensitive to input
                        menubar.set_sensitive(False)
                        # Also try to hide it
                        menubar.set_no_show_all(True)
                        menubar.hide()
                        gtk_window.set_menubar_visible(False)
                        
            except Exception as e:
                print(f"Could not disable GTK menubar completely: {e}")
                
        except Exception as e:
            print(f"Could not disable commands: {e}")
    
    def enable_commands(self):
        """Enable all menu commands when unlocked"""
        try:
            # Try to show the toolbar/menu widget
            if hasattr(self.main_window, '_impl') and hasattr(self.main_window._impl, 'toolbar'):
                self.main_window._impl.toolbar.set_visible(True)
            elif hasattr(self.main_window, 'toolbar'):
                self.main_window.toolbar.visible = True
            
            # Show GTK menu bar
            self.show_gtk_menubar()
            
            # Enable all commands
            for command in self.commands:
                command.enabled = True
            
            # Additional GTK menubar showing
            try:
                import gi
                gi.require_version('Gtk', '3.0')
                from gi.repository import Gtk
                
                gtk_window = self.main_window._impl.native
                
                # Try to restore menubar
                if hasattr(gtk_window, 'get_menubar'):
                    menubar = gtk_window.get_menubar()
                    if menubar:
                        menubar.set_sensitive(True)
                        menubar.set_no_show_all(False)
                        menubar.show()
                        gtk_window.set_menubar_visible(True)
                        
            except Exception as e:
                print(f"Could not enable GTK menubar completely: {e}")
                
        except Exception as e:
            print(f"Could not enable commands: {e}")
    
    def hide_gtk_menubar(self):
        """Hide GTK menu bar using direct GTK access"""
        try:
            import gi
            gi.require_version('Gtk', '3.0')
            from gi.repository import Gtk
            
            gtk_window = self.main_window._impl.native
            
            # Method 1: Try to hide the menubar widget using set_visible
            if hasattr(gtk_window, 'get_menubar'):
                menubar = gtk_window.get_menubar()
                if menubar:
                    menubar.set_visible(False)
                    return
            
            # Method 2: Search through window children and hide any menubar
            def find_and_hide_menubar(container):
                for child in container.get_children():
                    if isinstance(child, Gtk.MenuBar):
                        child.set_visible(False)
                        return True
                    elif hasattr(child, 'get_children'):
                        if find_and_hide_menubar(child):
                            return True
                return False
            
            find_and_hide_menubar(gtk_window)
            
            # Method 3: Try to apply CSS to hide menubar
            try:
                screen = Gtk.Window.get_default_screen()
                css_provider = Gtk.CssProvider()
                css_provider.load_from_data(b"menubar { visibility: hidden; }")
                style_context = Gtk.StyleContext()
                style_context.add_provider_for_screen(
                    screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
            except:
                pass
            
        except Exception as e:
            print(f"Could not hide GTK menubar: {e}")
    
    def show_gtk_menubar(self):
        """Show GTK menu bar using direct GTK access"""
        try:
            import gi
            gi.require_version('Gtk', '3.0')
            from gi.repository import Gtk
            
            gtk_window = self.main_window._impl.native
            
            # Method 1: Try to show the menubar widget using set_visible
            if hasattr(gtk_window, 'get_menubar'):
                menubar = gtk_window.get_menubar()
                if menubar:
                    menubar.set_visible(True)
                    return
            
            # Method 2: Search through window children and show any menubar
            def find_and_show_menubar(container):
                for child in container.get_children():
                    if isinstance(child, Gtk.MenuBar):
                        child.set_visible(True)
                        return True
                    elif hasattr(child, 'get_children'):
                        if find_and_show_menubar(child):
                            return True
                return False
            
            find_and_show_menubar(gtk_window)
            
            # Method 3: Try to apply CSS to show menubar
            try:
                screen = Gtk.Window.get_default_screen()
                css_provider = Gtk.CssProvider()
                css_provider.load_from_data(b"menubar { visibility: visible; }")
                style_context = Gtk.StyleContext()
                style_context.add_provider_for_screen(
                    screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
            except:
                pass
            
        except Exception as e:
            print(f"Could not show GTK menubar: {e}")
    
    def hide_menu_bar(self):
        """Hide the GTK menu bar - kept for compatibility"""
        pass
    
    def show_menu_bar(self):
        """Show the GTK menu bar - kept for compatibility"""
        pass
    
    def toggle_lock(self, widget):
        """Toggle between locked and unlocked state"""
        self.update_activity()  # Track user activity
        
        if self.is_locked:
            # If currently locked, attempt to unlock (this will show PIN prompt)
            self.attempt_unlock(widget)
        else:
            # If currently unlocked, lock immediately
            self.lock_app()
    
    def lock_app(self):
        """Lock the application"""
        self.is_locked = True
        self.config["lock"]["enabled"] = True
        self.save_config()
        self.lock_btn.text = '🔒'
        self.update_ui_visibility()
        self.log_label.text = "Application locked"
    
    async def attempt_unlock(self, widget):
        """Attempt to unlock the application with PIN"""
        lock_config = self.config.get("lock", {})
        stored_pin = lock_config.get("pin", "")
        
        if not stored_pin:
            # No PIN set, unlock immediately
            self.unlock_app()
            return
        
        entered_pin = self.pin_input.value or ""
        
        if entered_pin == stored_pin:
            self.unlock_app()
        else:
            self.unlock_status.text = "Incorrect PIN"
            self.pin_input.value = ""
    
    def unlock_app(self):
        """Unlock the application"""
        self.is_locked = False
        self.config["lock"]["enabled"] = False
        self.save_config()
        self.lock_btn.text = '🔓'
        self.update_ui_visibility()
        self.pin_input.value = ""
        self.unlock_status.text = ""
        self.last_activity = time.time()
        self.log_label.text = "Application unlocked"
    
    def start_auto_lock_timer(self):
        """Start the auto-lock timer if configured"""
        self.stop_auto_lock_timer()  # Stop any existing timer
        
        timeout_seconds = self.config.get("lock", {}).get("auto_lock_timeout", 0)
        if timeout_seconds > 0 and not self.is_locked:
            self.auto_lock_timer = threading.Timer(timeout_seconds, self.check_auto_lock)
            self.auto_lock_timer.daemon = True
            self.auto_lock_timer.start()
    
    def stop_auto_lock_timer(self):
        """Stop the auto-lock timer"""
        if self.auto_lock_timer:
            self.auto_lock_timer.cancel()
            self.auto_lock_timer = None
    
    def check_auto_lock(self):
        """Check if app should auto-lock due to inactivity"""
        if self.is_locked:
            return
            
        timeout_seconds = self.config.get("lock", {}).get("auto_lock_timeout", 0)
        if timeout_seconds > 0:
            if time.time() - self.last_activity >= timeout_seconds:
                # Auto-lock due to inactivity - must be called on main thread
                def auto_lock_task():
                    self.lock_app()
                    self.log_label.text = f"Auto-locked after {timeout_seconds} seconds of inactivity"
                    return False  # Remove from idle queue
                
                # Use GLib.idle_add to schedule on main thread
                try:
                    from gi.repository import GLib
                    GLib.idle_add(auto_lock_task)
                except ImportError:
                    # Fallback - just call directly (may still cause issues)
                    auto_lock_task()
            
            # Always schedule next check, regardless of whether we locked or not
            self.start_auto_lock_timer()
    
    def update_activity(self):
        """Update last activity timestamp and restart auto-lock timer"""
        self.last_activity = time.time()
        if not self.is_locked:
            self.start_auto_lock_timer()
    
    def toggle_theme(self, widget):
        """Toggle between light and dark theme"""
        self.update_activity()  # Track user activity
        
        current = self.config.get("theme", "light")
        new_theme = "dark" if current == "light" else "light"
        self.config["theme"] = new_theme
        self.save_config()
        self.apply_theme()
        # Update button icon
        self.theme_btn.text = '🌙' if new_theme == "light" else '☀️'
    
    def apply_theme(self):
        """Apply the current theme to the main window"""
        theme = self.config.get("theme", "light")
        
        # For GTK (Linux), we need to set the GTK theme using CSS
        try:
            import gi
            gi.require_version('Gtk', '3.0')
            gi.require_version('Gdk', '3.0')
            from gi.repository import Gtk, Gdk
            
            # First try to set the prefer dark theme property
            settings = Gtk.Settings.get_default()
            if settings:
                prefer_dark = (theme == "dark")
                settings.set_property("gtk-application-prefer-dark-theme", prefer_dark)
                print(f"Set gtk-application-prefer-dark-theme to: {prefer_dark}")
            
            # Additionally, inject custom CSS to ensure colors are applied
            if theme == "dark":
                css_data = """
                window {
                    background-color: #404040;
                    color: #ffffff;
                }
                box, label {
                    background-color: #404040;
                    color: #ffffff;
                }
                button {
                    background-image: none;
                    background-color: #404040;
                    color: #ffffff;
                    border: 1px solid #ffffff;
                    border-radius: 5px;
                    outline: none;
                    box-shadow: none;
                }
                button:hover {
                    background-image: none;
                    background-color: #404040;
                    color: #ffffff;
                    border: 3px solid #178298;
                    outline: none;
                    box-shadow: none;
                }
                entry {
                    background-color: #ffffff;
                    color: #000000;
                    border: 3px solid #ffffff;
                }
                menubar, menu, menuitem {
                    background-color: #404040;
                    color: #ffffff;
                }
                """
            else:
                css_data = """
                window {
                    background-color: #ffffff;
                    color: #000000;
                }
                box, button, entry, label {
                    background-color: #ffffff;
                    color: #000000;
                }
                menubar, menu, menuitem {
                    background-color: #ffffff;
                    color: #404040;
                }
                """
            
            # Apply the CSS
            css_provider = Gtk.CssProvider()
            css_provider.load_from_data(css_data.encode())
            screen = Gdk.Screen.get_default()
            style_context = Gtk.StyleContext()
            style_context.add_provider_for_screen(
                screen,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            print(f"Applied {theme} theme CSS")
            
        except Exception as e:
            print(f"Could not apply GTK theme: {e}")
            import traceback
            traceback.print_exc()
        
        # Update status label color
        if hasattr(self, 'status_label'):
            status_color = '#00ff00' if self.ser and self.ser.is_open else '#ff0000'
            self.status_label.style.color = status_color
    
    def shutdown(self):
        """Called when the app is about to exit"""
        self.stop_auto_lock_timer()  # Stop the auto-lock timer
        
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        return True
    
    def create_menu(self):
        """Create application menu"""
        # Create command group for the app menu
        # Add reset command to the main app menu (where Quit is)
        reset_cmd = toga.Command(
            self.reset_settings,
            text='Clear All Settings',
            tooltip='Reset all button names and disconnect Arduino',
            group=toga.Group.APP
        )
        
        lock_cmd = toga.Command(
            self.change_lock_pin,
            text='Set Lock PIN',
            tooltip='Change or set the lock PIN for the application',
            group=toga.Group.APP
        )

        self.commands.add(reset_cmd)
        self.commands.add(lock_cmd)

    
    async def reset_settings(self, widget):
        """Reset all settings to default values"""
        # Check if PIN is set and require authentication
        lock_config = self.config.get("lock", {})
        pin_required = lock_config.get("pin", "")

        if pin_required:
            # PIN is set, require authentication - use async dialog
            pin_input = await self.show_pin_input_dialog(
                "Reset Settings",
                "Enter your PIN to reset all settings:"
            )

            if pin_input is None:  # User cancelled
                return

            if pin_input != pin_required:
                # Show error message using a non-blocking dialog
                await self.main_window.dialog(
                    toga.ErrorDialog(
                        "Authentication Failed",
                        "Incorrect PIN. Settings reset cancelled."
                    )
                )
                return

        # Ask for confirmation using a non-blocking dialog
        confirmed = await self.main_window.dialog(
            toga.QuestionDialog(
                "Reset Settings",
                "Are you sure you want to reset all settings to default? This will reset all button names and disconnect the Arduino."
            )
        )

        if not confirmed:
            return

        # Disconnect Arduino if connected
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.status_label.text = "❌ Disconnected"
            self.status_label.style.color = '#FF0000'
            self.connect_btn.enabled = True
            self.disconnect_btn.enabled = False
            self.log_label.text = "Arduino disconnected"

        # Reset config to defaults
        self.config = self.default_settings().copy()
        self.button_labels = self.config["labels"].copy()
        self.save_config()

        # Update button labels in UI
        for key, button in self.buttons.items():
            button.text = self.button_labels[key]

        # Apply theme
        self.apply_theme()
        self.theme_btn.text = '🌙' if self.config.get("theme", "light") == "light" else '☀️'

        # Show success message using a non-blocking dialog
        await self.main_window.dialog(
            toga.InfoDialog(
                'Settings Reset',
                'All settings have been reset to their default values.'
            )
        )
    
    def show_error_message(self, title, message):
        """Show a simple error message dialog"""
        dialog_window = toga.Window(title=title)
        dialog_box = toga.Box(style=Pack(direction=COLUMN, margin=20))
        
        label = toga.Label(message, style=Pack(margin_bottom=20))
        dialog_box.add(label)
        
        def on_ok(widget):
            dialog_window.close()
        
        ok_button = toga.Button("OK", on_press=on_ok, style=Pack(width=100))
        dialog_box.add(ok_button)
        
        dialog_window.content = dialog_box
        dialog_window.show()
        
        # Wait for dialog
        import time
        while dialog_window._impl.native.get_visible():
            time.sleep(0.1)
    
    def show_success_message(self, title, message):
        """Show a simple success message dialog"""
        dialog_window = toga.Window(title=title)
        dialog_box = toga.Box(style=Pack(direction=COLUMN, margin=20))
        
        label = toga.Label(message, style=Pack(margin_bottom=20))
        dialog_box.add(label)
        
        def on_ok(widget):
            dialog_window.close()
        
        ok_button = toga.Button("OK", on_press=on_ok, style=Pack(width=100))
        dialog_box.add(ok_button)
        
        dialog_window.content = dialog_box
        dialog_window.show()
        
        # Wait for dialog
        import time
        while dialog_window._impl.native.get_visible():
            time.sleep(0.1)
    
    async def show_pin_input_dialog(self, title, message):
        """Show a PIN input dialog and return the entered PIN or None if cancelled"""
        # Create a custom dialog window for PIN input without blocking the main loop
        dialog_window = toga.Window(title=title)
        dialog_box = toga.Box(style=Pack(direction=COLUMN, margin=20))

        # Centered lock icon for visual context
        icon_row = toga.Box(style=Pack(direction=ROW, margin_bottom=10))
        icon_row.add(toga.Box(style=Pack(flex=1)))
        icon_row.add(
            toga.Label(
                '🔒',
                style=Pack(font_size=36, text_align='center')
            )
        )
        icon_row.add(toga.Box(style=Pack(flex=1)))
        dialog_box.add(icon_row)

        label = toga.Label(
            message,
            style=Pack(margin_bottom=10, text_align='center')
        )
        dialog_box.add(label)

        pin_input = toga.PasswordInput(
            placeholder='Enter PIN',
            style=Pack(margin_bottom=10, width=250)
        )

        pin_row = toga.Box(style=Pack(direction=ROW, margin_bottom=10))
        pin_row.add(toga.Box(style=Pack(flex=1)))
        pin_row.add(pin_input)
        pin_row.add(toga.Box(style=Pack(flex=1)))
        dialog_box.add(pin_row)

        button_box = toga.Box(style=Pack(direction=ROW))

        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def on_ok(widget):
            if not future.done():
                future.set_result(pin_input.value or "")
            dialog_window.close()

        def on_cancel(widget):
            if not future.done():
                future.set_result(None)
            dialog_window.close()

        ok_button = toga.Button(
            "OK",
            on_press=on_ok,
            style=Pack(flex=1, margin_right=5)
        )
        button_box.add(ok_button)

        cancel_button = toga.Button(
            "Cancel",
            on_press=on_cancel,
            style=Pack(flex=1)
        )
        button_box.add(cancel_button)

        button_row = toga.Box(style=Pack(direction=ROW, margin_top=10))
        button_row.add(toga.Box(style=Pack(flex=1)))
        button_row.add(button_box)
        button_row.add(toga.Box(style=Pack(flex=1)))
        dialog_box.add(button_row)
        dialog_window.content = dialog_box
        dialog_window.show()

        # Await the user's choice without blocking the UI thread
        return await future
    async def change_lock_pin(self, widget):
        """Change or set the lock PIN"""
        # Create a dialog for PIN change
        pin_dialog = toga.Window(title="Set Lock PIN")
        dialog_box = toga.Box(style=Pack(direction=COLUMN, margin=20))
        
        current_pin = self.config.get("lock", {}).get("pin", "")
        
        if current_pin:
            label_text = "Enter current PIN to change:"
        else:
            label_text = "Set a new PIN (leave empty to disable lock):"
        
        label = toga.Label(
            label_text,
            style=Pack(margin_bottom=10)
        )
        dialog_box.add(label)
        
        current_pin_input = toga.PasswordInput(
            placeholder='Current PIN' if current_pin else 'New PIN',
            style=Pack(margin_bottom=10, width=250)
        )
        dialog_box.add(current_pin_input)
        
        if current_pin:
            new_pin_label = toga.Label(
                "Enter new PIN:",
                style=Pack(margin_bottom=10)
            )
            dialog_box.add(new_pin_label)
            
            new_pin_input = toga.PasswordInput(
                placeholder='New PIN',
                style=Pack(margin_bottom=10, width=250)
            )
            dialog_box.add(new_pin_input)
            
            confirm_pin_label = toga.Label(
                "Confirm new PIN:",
                style=Pack(margin_bottom=10)
            )
            dialog_box.add(confirm_pin_label)
            
            confirm_pin_input = toga.PasswordInput(
                placeholder='Confirm New PIN',
                style=Pack(margin_bottom=10, width=250)
            )
            dialog_box.add(confirm_pin_input)
        
        # Auto-lock timeout setting
        timeout_label = toga.Label(
            "Auto-lock timeout (seconds, 0 = disabled):",
            style=Pack(margin_bottom=10)
        )
        dialog_box.add(timeout_label)
        
        current_timeout = str(self.config.get("lock", {}).get("auto_lock_timeout", 0))
        timeout_input = toga.TextInput(
            value=current_timeout,
            placeholder='0',
            style=Pack(margin_bottom=10, width=250)
        )
        dialog_box.add(timeout_input)
        
        status_label = toga.Label(
            '',
            style=Pack(margin_bottom=10, text_align='center', color='#FF0000')
        )
        dialog_box.add(status_label)
        
        button_box = toga.Box(style=Pack(direction=ROW, margin_top=10))
        
        def on_save(widget):
            if current_pin:
                # Changing existing PIN
                if current_pin_input.value != current_pin:
                    status_label.text = "Current PIN is incorrect"
                    return
                
                new_pin = new_pin_input.value or ""
                confirm_pin = confirm_pin_input.value or ""
                
                if new_pin != confirm_pin:
                    status_label.text = "New PINs don't match"
                    return
                
                if not new_pin:
                    # Disable lock
                    self.config["lock"]["pin"] = ""
                    self.config["lock"]["enabled"] = False
                    self.is_locked = False
                    self.lock_btn.text = '🔓'
                    self.update_ui_visibility()
                    status_label.text = "Lock disabled"
                    status_label.style.color = '#00FF00'
                else:
                    self.config["lock"]["pin"] = new_pin
                    status_label.text = "PIN changed successfully"
                    status_label.style.color = '#00FF00'
            else:
                # Setting new PIN
                new_pin = current_pin_input.value or ""
                if not new_pin:
                    self.config["lock"]["pin"] = ""
                    self.config["lock"]["enabled"] = False
                    self.is_locked = False
                    self.lock_btn.text = '🔓'
                    self.update_ui_visibility()
                    status_label.text = "Lock disabled"
                    status_label.style.color = '#00FF00'
                else:
                    self.config["lock"]["pin"] = new_pin
                    status_label.text = "PIN set successfully"
                    status_label.style.color = '#00FF00'
            
            # Save auto-lock timeout
            try:
                timeout_value = int(timeout_input.value or "0")
                if timeout_value < 0:
                    timeout_value = 0
                self.config["lock"]["auto_lock_timeout"] = timeout_value
                if timeout_value > 0:
                    self.start_auto_lock_timer()
                else:
                    self.stop_auto_lock_timer()
            except ValueError:
                status_label.text = "Invalid timeout value"
                status_label.style.color = '#FF0000'
                return
            
            self.save_config()
            pin_dialog.close()  # Close the dialog after successful save
        
        def on_cancel(widget):
            pin_dialog.close()
        
        save_button = toga.Button(
            "Save",
            on_press=on_save,
            style=Pack(flex=1, margin_right=5)
        )
        button_box.add(save_button)
        
        cancel_button = toga.Button(
            "Cancel",
            on_press=on_cancel,
            style=Pack(flex=1)
        )
        button_box.add(cancel_button)
        
        dialog_box.add(button_box)
        pin_dialog.content = dialog_box
        pin_dialog.show()
    
    def create_button_row(self, parent_box, key):
        """Create a button with rename functionality"""
        button_box = toga.Box(style=Pack(direction=ROW, margin=5, flex=1))
        
        main_btn = toga.Button(
            self.button_labels[key],
            on_press=self.make_send_handler(key),
            style=Pack(flex=1, margin_right=5)
        )
        button_box.add(main_btn)
        
        rename_btn = toga.Button(
            '✏️',
            on_press=self.make_rename_handler(key, main_btn),
            style=Pack(width=40)
        )
        button_box.add(rename_btn)
        
        self.buttons[key] = main_btn
        parent_box.add(button_box)
    
    def make_send_handler(self, key):
        """Create a handler for sending commands"""
        async def handler(widget):
            await self.send_command(key)
        return handler
    
    def make_rename_handler(self, key, button_widget):
        """Create a handler for renaming buttons"""
        async def handler(widget):
            await self.rename_button(key, button_widget)
        return handler
    
    def refresh_ports(self, widget):
        """Refresh the list of available serial ports"""
        ports = self.list_serial_ports()
        self.port_selection.items = ports
        if ports and ports[0] != "No ports found":
            self.port_selection.value = ports[0]
    
    async def connect_arduino(self, widget):
        """Connect to the selected Arduino port"""
        self.update_activity()  # Track user activity
        
        port = self.port_selection.value
        if not port or port == "No ports found":
            await self.main_window.dialog(
                toga.InfoDialog("No Port Selected", "Please select a valid serial port.")
            )
            return
        
        try:
            self.ser = serial.Serial(port, 9600, timeout=1)
            time.sleep(2)
            self.status_label.text = f"✅ Connected: {port}"
            self.status_label.style.color = '#00FF00'
            self.connect_btn.enabled = False
            self.disconnect_btn.enabled = True
            self.log_label.text = f"Connected to {port}"
        except Exception as e:
            await self.main_window.dialog(
                toga.ErrorDialog("Connection Error", str(e))
            )
    
    def disconnect_arduino(self, widget):
        """Disconnect from the Arduino"""
        self.update_activity()  # Track user activity
        
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.status_label.text = "❌ Disconnected"
            self.status_label.style.color = '#FF0000'
            self.connect_btn.enabled = True
            self.disconnect_btn.enabled = False
            self.log_label.text = "Arduino disconnected"
    
    async def send_command(self, cmd):
        """Send a command to the Arduino"""
        self.update_activity()  # Track user activity
        
        if self.ser and self.ser.is_open:
            self.ser.write((cmd + "\n").encode())
            self.log_label.text = f"Sent: {cmd}"
        else:
            await self.main_window.dialog(
                toga.InfoDialog("Not Connected", "Connect to Arduino first!")
            )
    
    async def send_custom_command(self, widget):
        """Send custom command from text input"""
        cmd = self.custom_entry.value
        if cmd:
            await self.send_command(cmd)
            self.custom_entry.value = ""
    
    async def rename_button(self, key, button_widget):
        """Rename a button and save to config"""
        # Create a custom dialog window for text input
        dialog_window = toga.Window(title="Rename Button")
        dialog_box = toga.Box(style=Pack(direction=COLUMN, margin=20))
        
        label = toga.Label(
            "Enter new button name:",
            style=Pack(margin_bottom=10)
        )
        dialog_box.add(label)
        
        text_input = toga.TextInput(
            value=self.button_labels[key],
            style=Pack(margin_bottom=10, width=250)
        )
        dialog_box.add(text_input)
        
        button_box = toga.Box(style=Pack(direction=ROW, margin_top=10))
        
        def on_ok(widget):
            new_name = text_input.value
            if new_name and new_name.strip():
                button_widget.text = new_name
                self.button_labels[key] = new_name
                self.config["labels"] = self.button_labels
                self.save_config()
            dialog_window.close()
        
        def on_cancel(widget):
            dialog_window.close()
        
        ok_button = toga.Button(
            "OK",
            on_press=on_ok,
            style=Pack(flex=1, margin_right=5)
        )
        button_box.add(ok_button)
        
        cancel_button = toga.Button(
            "Cancel",
            on_press=on_cancel,
            style=Pack(flex=1)
        )
        button_box.add(cancel_button)
        
        dialog_box.add(button_box)
        dialog_window.content = dialog_box
        dialog_window.show()


def main():
    return ArduinoControlApp()


if __name__ == '__main__':
    main().main_loop()