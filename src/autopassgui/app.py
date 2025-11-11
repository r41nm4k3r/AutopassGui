import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import serial
import serial.tools.list_ports
import time
import json
import os
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
    
    def default_settings(self):
        """Return default configuration settings"""
        return {
            "labels": {
                "password1": "Send Password 1",
                "password2": "Send Password 2",
                "password3": "Send Password 3",
                "password4": "Send Password 4"
            },
            "theme": "dark"
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
        spacer = toga.Box(style=Pack(flex=1))  # Push button to the right
        theme_box.add(spacer)
        
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
        self.apply_theme()
        self.main_window.show()
    
    def toggle_theme(self, widget):
        """Toggle between light and dark theme"""
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

        self.commands.add(reset_cmd)

    
    async def reset_settings(self, widget):
        """Reset all settings to default values"""
        # Ask for confirmation
        confirm = await self.main_window.question_dialog(
            'Reset Settings',
            'Are you sure you want to reset all settings to default? This will reset all button names and disconnect the Arduino.'
        )
        
        if confirm:
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
            
            await self.main_window.info_dialog(
                'Settings Reset',
                'All settings have been reset to their default values.'
            )
    
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
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.status_label.text = "❌ Disconnected"
            self.status_label.style.color = '#FF0000'
            self.connect_btn.enabled = True
            self.disconnect_btn.enabled = False
            self.log_label.text = "Arduino disconnected"
    
    async def send_command(self, cmd):
        """Send a command to the Arduino"""
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