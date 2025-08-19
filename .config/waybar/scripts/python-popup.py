#!/usr/bin/env python3
import gi, subprocess
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gdk

# --- Helper functions ---
def run_command(cmd_list):
    """Run a shell command and return its stripped stdout."""
    try:
        output = subprocess.run(cmd_list, capture_output=True, text=True, check=True)
        return output.stdout.strip()
    except subprocess.CalledProcessError:
        return "N/A"

def value_to_class(value, thresholds, reverse=False):
    """
    Returns a CSS class name based on numeric value and thresholds.
    thresholds: list of numbers in ascending order, e.g. [60, 80, 90]
    The mapping will be:
      value <= thresholds[0] : green-low
      thresholds[0] < value <= thresholds[1] : yellow-mid
      thresholds[1] < value <= thresholds[2] : red-dark
      value > thresholds[2] : red-bright
    reverse=True inverts the mapping.
    """
    try:
        val = float(value)
    except:
        return "green-low"

    if reverse:
        if val <= thresholds[0]:
            return "green-low"
        elif val <= thresholds[1]:
            return "yellow-mid"
        elif val <= thresholds[2]:
            return "red-dark"
        else:
            return "red-bright"
    else:
        if val <= thresholds[0]:
            return "red-bright"
        elif val <= thresholds[1]:
            return "red-dark"
        elif val <= thresholds[2]:
            return "yellow-mid"
        else:
            return "green-low"

# --- GTK Window ---
class SysinfoPopup(Gtk.Window):
    def __init__(self):
        super().__init__(title="Sysinfo Popup")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(260, 180)
        self.set_opacity(0.95)

        # Close when losing focus
        self.set_modal(True)        # grabs input
        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect("leave", lambda c: self.close())
        self.add_controller(focus_controller)

        self.set_transient_for(None)

        # Main vertical box
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.vbox.set_margin_top(10)
        self.vbox.set_margin_bottom(10)
        self.vbox.set_margin_start(10)
        self.vbox.set_margin_end(10)
        self.set_child(self.vbox)

        # Create rows for each metric
        self.cpu_row = self.create_row()
        self.gpu_row = self.create_row()
        self.root_row = self.create_row()
        self.home_row = self.create_row()

        # Add rows to vertical box
        for row in [self.cpu_row, self.gpu_row, self.root_row, self.home_row]:
            self.vbox.append(row)

        # Load CSS
        self.load_css()

        # Initial update
        self.update_info()
        GLib.timeout_add_seconds(1, self.update_info)

        self.present()  # gives focus to the window

    def create_row(self):
        """Creates a horizontal box with left-aligned label and right-aligned value."""
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_spacing(0)

        label = Gtk.Label(xalign=0)
        label.set_hexpand(True)

        value = Gtk.Label(xalign=1)
        value.set_hexpand(True)

        hbox.append(label)
        hbox.append(value)
        hbox.label = label
        hbox.value = value
        return hbox

    def load_css(self):
        css = b"""
        .green-low { background-color: rgba(0,255,0,0.2); color: white; font: 18px Monospace; padding: 4px 6px; font-weight: bold; }
        .yellow-mid { background-color: rgba(255,255,0,0.4); color: white; font: 18px Monospace; padding: 4px 6px; font-weight: bold; }
        .red-dark { background-color: rgba(255,0,0,0.3); color: white; font: 18px Monospace; padding: 4px 6px; font-weight: bold; }
        .red-bright { background-color: rgba(255,0,0,0.7); color: white; font: 18px Monospace; padding: 4px 6px; font-weight: bold; }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def update_info(self):
        # --- Read values ---
        cpu_temp = run_command(['sensors'])
        cpu_val = "N/A"
        for line in cpu_temp.splitlines():
            if "Package id 0:" in line:
                cpu_val = line.split()[3].replace('+','').replace('°C','')
                break

        gpu_val = run_command(['nvidia-smi','--query-gpu=temperature.gpu','--format=csv,noheader,nounits'])
        disk_root = run_command(['df','-h','/']).splitlines()[1].split()[3].replace('G','')
        disk_home = run_command(['df','-h','/home']).splitlines()[1].split()[3].replace('G','')

        # --- Determine classes ---
        cpu_class = value_to_class(cpu_val, [60, 80, 90], True)
        gpu_class = value_to_class(gpu_val, [60, 75, 80], True)
        root_class = value_to_class(disk_root, [5, 10, 20])
        home_class = value_to_class(disk_home, [50, 100, 200])

        # --- Update rows ---
        self.set_row(self.cpu_row, "CPU Temp:", cpu_val+"°C", cpu_class)
        self.set_row(self.gpu_row, "GPU Temp:", gpu_val+"°C", gpu_class)
        self.set_row(self.root_row, "/ Free:", disk_root+"G", root_class)
        self.set_row(self.home_row, "/home Free:", disk_home+"G", home_class)

        return True

    def set_row(self, row, label_text, value_text, css_class):
        row.label.set_text(label_text)
        row.value.set_text(value_text)

        # Remove old classes and add new
        for widget in [row.label, row.value]:
            ctx = widget.get_style_context()
            for cls in ["green-low","yellow-mid","red-dark","red-bright"]:
                ctx.remove_class(cls)
            ctx.add_class(css_class)

# --- Run the popup ---
win = SysinfoPopup()
win.present()

# GTK4 main loop
loop = GLib.MainLoop()
loop.run()

