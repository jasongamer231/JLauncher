import os
import json
import shutil
import threading
import subprocess
import time
import urllib.parse
import requests
import urllib3
import customtkinter as ctk
import minecraft_launcher_lib

# Disable SSL warnings when bypassing certificate verification on macOS
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Optional Discord RPC Support
try:
    import pypresence
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False

# Predefined Theme Color Palettes
THEMES = {
    "Sunset (Default)": {
        "bg": "#120E16", "card": "#1E1724", "sidebar": "#18121E",
        "orange": "#FF9F1C", "hover": "#FFBF69", "gold": "#FFBF69", "red": "#FF6B6B", "text": "#FBE8E7"
    },
    "Emerald Green": {
        "bg": "#0D1612", "card": "#17261E", "sidebar": "#111C17",
        "orange": "#2ECC71", "hover": "#27AE60", "gold": "#F1C40F", "red": "#E74C3C", "text": "#E8FBEE"
    },
    "Cyberpunk Pink": {
        "bg": "#120B16", "card": "#1E1424", "sidebar": "#170F1E",
        "orange": "#FF007F", "hover": "#D8006C", "gold": "#00F0FF", "red": "#FF4D4D", "text": "#FBE7F5"
    },
    "Ocean Blue": {
        "bg": "#0B1216", "card": "#141E24", "sidebar": "#0F171E",
        "orange": "#3498DB", "hover": "#2980B9", "gold": "#5DADE2", "red": "#E74C3C", "text": "#E7F3FB"
    }
}

class AddInstanceDialog(ctk.CTkToplevel):
    """Popup window for creating a new Minecraft instance with Modloader support."""
    def __init__(self, parent, versions, theme, callback):
        super().__init__(parent)
        self.title("New Instance")
        self.geometry("380x350")
        self.resizable(False, False)
        self.configure(fg_color=theme["bg"])
        self.callback = callback
        self.grab_set()

        self.title_lbl = ctk.CTkLabel(
            self, text="Create New Instance", 
            font=ctk.CTkFont(size=15, weight="bold"), text_color=theme["gold"]
        )
        self.title_lbl.pack(pady=(25, 10))

        self.name_entry = ctk.CTkEntry(
            self, placeholder_text="Instance Name (e.g. Lifesteal)", 
            width=300, height=36, corner_radius=6,
            fg_color=theme["bg"], border_color=theme["orange"], text_color=theme["text"]
        )
        self.name_entry.pack(pady=8)

        self.loader_lbl = ctk.CTkLabel(self, text="MODLOADER", font=ctk.CTkFont(size=10, weight="bold"), text_color=theme["orange"])
        self.loader_lbl.pack(anchor="w", padx=40, pady=(6, 2))
        self.loader_option = ctk.CTkOptionMenu(
            self, values=["Vanilla", "Fabric", "Forge / NeoForge"], width=300, height=36, corner_radius=6,
            fg_color=theme["card"], button_color=theme["orange"], button_hover_color=theme["hover"],
            text_color=theme["text"]
        )
        self.loader_option.pack(pady=4)

        self.ver_lbl = ctk.CTkLabel(self, text="GAME VERSION", font=ctk.CTkFont(size=10, weight="bold"), text_color=theme["orange"])
        self.ver_lbl.pack(anchor="w", padx=40, pady=(6, 2))
        self.ver_option = ctk.CTkOptionMenu(
            self, values=versions, width=300, height=36, corner_radius=6,
            fg_color=theme["card"], button_color=theme["orange"], button_hover_color=theme["hover"],
            text_color=theme["text"]
        )
        self.ver_option.pack(pady=4)
        if versions:
            self.ver_option.set(versions[0])

        self.create_btn = ctk.CTkButton(
            self, text="CREATE INSTANCE", font=ctk.CTkFont(size=11, weight="bold"),
            width=300, height=38, corner_radius=6, fg_color=theme["orange"], hover_color=theme["hover"],
            text_color="#141017", command=self.on_create
        )
        self.create_btn.pack(pady=(20, 20))

    def on_create(self):
        name = self.name_entry.get().strip()
        version = self.ver_option.get()
        loader = self.loader_option.get()
        if name:
            self.callback(name, version, loader)
            self.destroy()


class EditInstanceDialog(ctk.CTkToplevel):
    """Popup window for editing an instance's details."""
    def __init__(self, parent, instance, versions, theme, callback):
        super().__init__(parent)
        self.title("Edit Instance")
        self.geometry("380x350")
        self.resizable(False, False)
        self.configure(fg_color=theme["bg"])
        self.callback = callback
        self.grab_set()

        self.old_name = instance["name"]

        self.title_lbl = ctk.CTkLabel(
            self, text=f"Edit '{self.old_name}'", 
            font=ctk.CTkFont(size=15, weight="bold"), text_color=theme["gold"]
        )
        self.title_lbl.pack(pady=(25, 10))

        self.name_entry = ctk.CTkEntry(
            self, width=300, height=36, corner_radius=6,
            fg_color=theme["bg"], border_color=theme["orange"], text_color=theme["text"]
        )
        self.name_entry.pack(pady=8)
        self.name_entry.insert(0, self.old_name)

        self.loader_lbl = ctk.CTkLabel(self, text="MODLOADER TYPE", font=ctk.CTkFont(size=10, weight="bold"), text_color=theme["orange"])
        self.loader_lbl.pack(anchor="w", padx=40, pady=(6, 2))
        self.loader_option = ctk.CTkOptionMenu(
            self, values=["Vanilla", "Fabric", "Forge / NeoForge"], width=300, height=36, corner_radius=6,
            fg_color=theme["card"], button_color=theme["orange"], button_hover_color=theme["hover"],
            text_color=theme["text"]
        )
        self.loader_option.pack(pady=4)
        self.loader_option.set(instance.get("loader", "Vanilla"))

        self.ver_lbl = ctk.CTkLabel(self, text="GAME VERSION", font=ctk.CTkFont(size=10, weight="bold"), text_color=theme["orange"])
        self.ver_lbl.pack(anchor="w", padx=40, pady=(6, 2))
        self.ver_option = ctk.CTkOptionMenu(
            self, values=versions, width=300, height=36, corner_radius=6,
            fg_color=theme["card"], button_color=theme["orange"], button_hover_color=theme["hover"],
            text_color=theme["text"]
        )
        self.ver_option.pack(pady=4)
        if instance["version"] in versions:
            self.ver_option.set(instance["version"])

        self.save_btn = ctk.CTkButton(
            self, text="SAVE CHANGES", font=ctk.CTkFont(size=11, weight="bold"),
            width=300, height=38, corner_radius=6, fg_color=theme["orange"], hover_color=theme["hover"],
            text_color="#141017", command=self.on_save
        )
        self.save_btn.pack(pady=(20, 20))

    def on_save(self):
        new_name = self.name_entry.get().strip()
        new_version = self.ver_option.get()
        new_loader = self.loader_option.get()
        if new_name:
            self.callback(self.old_name, new_name, new_version, new_loader)
            self.destroy()


class ManageContentDialog(ctk.CTkToplevel):
    """Popup window to manage and delete installed mods, resource packs, and shaders."""
    def __init__(self, parent, instance, theme):
        super().__init__(parent)
        self.title(f"Manage Content - {instance['name']}")
        self.geometry("460x500")
        self.resizable(False, False)
        self.configure(fg_color=theme["bg"])
        self.instance = instance
        self.theme = theme
        self.grab_set()

        title_lbl = ctk.CTkLabel(
            self, text=f"INSTALLED CONTENT: {instance['name'].upper()}", 
            font=ctk.CTkFont(size=12, weight="bold"), text_color=theme["gold"]
        )
        title_lbl.pack(pady=(20, 10))

        self.scroll_frame = ctk.CTkScrollableFrame(
            self, fg_color=theme["bg"], corner_radius=8
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.populate_content()

    def populate_content(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        instance_path = self.instance.get("path")
        if not instance_path or not os.path.exists(instance_path):
            return

        categories = [("MODS", "mods"), ("RESOURCE PACKS", "resourcepacks"), ("SHADERS", "shaderpacks")]
        has_items = False

        for cat_title, folder_name in categories:
            folder_path = os.path.join(instance_path, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            files = os.listdir(folder_path)
            files = [f for f in files if not f.startswith(".")]

            if files:
                has_items = True
                header_lbl = ctk.CTkLabel(
                    self.scroll_frame, text=cat_title, 
                    font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme["orange"], anchor="w"
                )
                header_lbl.pack(fill="x", padx=10, pady=(14, 4))

                for file_name in files:
                    file_path = os.path.join(folder_path, file_name)
                    card = ctk.CTkFrame(self.scroll_frame, fg_color=self.theme["card"], corner_radius=6, border_width=1, border_color=self.theme["sidebar"])
                    card.pack(fill="x", padx=6, pady=4)

                    name_lbl = ctk.CTkLabel(
                        card, text=file_name, font=ctk.CTkFont(size=11), text_color=self.theme["text"], anchor="w"
                    )
                    name_lbl.pack(side="left", padx=12, pady=8, fill="x", expand=True)

                    del_btn = ctk.CTkButton(
                        card, text="DELETE", font=ctk.CTkFont(size=10, weight="bold"),
                        width=70, height=26, corner_radius=4, fg_color=self.theme["red"], hover_color="#C0392B",
                        text_color="#FFF", command=lambda fp=file_path: self.delete_file(fp)
                    )
                    del_btn.pack(side="right", padx=10, pady=8)

        if not has_items:
            empty_lbl = ctk.CTkLabel(
                self.scroll_frame, text="No mods, resource packs, or shaders installed yet.", 
                font=ctk.CTkFont(size=11), text_color=self.theme["text"]
            )
            empty_lbl.pack(pady=40)

    def delete_file(self, file_path):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted {file_path}")
                self.populate_content()
        except Exception as e:
            print(f"Error deleting file: {e}")


class SelectInstanceDialog(ctk.CTkToplevel):
    """Popup window to choose which instance to install content into."""
    def __init__(self, parent, instances, project_type, theme, callback):
        super().__init__(parent)
        self.title("Select Target Instance")
        self.geometry("365x250")
        self.resizable(False, False)
        self.configure(fg_color=theme["bg"])
        self.callback = callback
        self.grab_set()

        if project_type == "mod":
            self.target_instances = [inst for inst in instances if inst.get("loader") in ["Fabric", "Forge / NeoForge"]]
            warning_text = "No Fabric or Forge instances found!\nPlease create a modded instance first."
        else:
            self.target_instances = instances
            warning_text = "No instances found!"

        title_lbl = ctk.CTkLabel(
            self, text="CHOOSE TARGET INSTANCE", 
            font=ctk.CTkFont(size=12, weight="bold"), text_color=theme["gold"]
        )
        title_lbl.pack(pady=(25, 10))

        if not self.target_instances:
            warn_lbl = ctk.CTkLabel(
                self, text=warning_text, 
                font=ctk.CTkFont(size=11), text_color=theme["red"], justify="center"
            )
            warn_lbl.pack(pady=10)
            
            close_btn = ctk.CTkButton(
                self, text="CLOSE", width=140, height=34, corner_radius=6,
                fg_color=theme["card"], text_color=theme["text"], command=self.destroy
            )
            close_btn.pack(pady=15)
            return

        instance_names = [inst["name"] for inst in self.target_instances]

        self.inst_option = ctk.CTkOptionMenu(
            self, values=instance_names, width=280, height=36, corner_radius=6,
            fg_color=theme["card"], button_color=theme["orange"], button_hover_color=theme["hover"],
            text_color=theme["text"]
        )
        self.inst_option.pack(pady=10)
        self.inst_option.set(instance_names[0])

        confirm_btn = ctk.CTkButton(
            self, text="INSTALL NOW", font=ctk.CTkFont(size=11, weight="bold"),
            width=280, height=38, corner_radius=6, fg_color=theme["orange"], hover_color=theme["hover"],
            text_color="#141017", command=self.on_confirm
        )
        confirm_btn.pack(pady=(15, 20))

    def on_confirm(self):
        selected_name = self.inst_option.get()
        for inst in self.target_instances:
            if inst["name"] == selected_name:
                self.callback(inst)
                break
        self.destroy()


class MinecraftLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("JLauncher - v1.0.0")
        self.geometry("980x640")
        self.resizable(False, False)

        self.base_dir = os.path.expanduser("~/Library/Application Support/JLauncher")
        self.instances_dir = os.path.join(self.base_dir, "instances")
        os.makedirs(self.instances_dir, exist_ok=True)

        self.max_progress = 100
        self.current_project_type = "mod"
        self.all_versions = self.get_vanilla_versions()
        self.config = self.load_config()

        # Set appearance mode (Dark/Light)
        app_mode = self.config.get("appearance_mode", "Dark")
        ctk.set_appearance_mode(app_mode)

        # Load active theme or custom RGB settings
        self.load_active_theme()
        self.configure(fg_color=self.theme["bg"])

        self.rpc_client = None
        self.rpc_start_time = int(time.time())
        self.setup_ui_layout()
        self.init_discord_rpc()

    def init_discord_rpc(self):
        if not DISCORD_AVAILABLE:
            return
        try:
            self.rpc_client = pypresence.Presence("1563902152739528825")
            self.rpc_client.connect()
            self.update_rpc("In Menus", "Viewing the Home Page")
        except Exception as e:
            print(f"Discord RPC Error: {e}")
            self.rpc_client = None

    def update_rpc(self, details, state):
        if self.rpc_client:
            try:
                self.rpc_client.update(
                    details=details,
                    state=state,
                    start=self.rpc_start_time
                )
            except Exception:
                pass

    def load_active_theme(self):
        app_mode = self.config.get("appearance_mode", "Dark")
        theme_name = self.config.get("theme", "Sunset (Default)")

        if theme_name == "Custom Customization":
            accent_rgb = self.config.get("custom_accent_rgb", [255, 159, 28])
            bg_rgb = self.config.get("custom_bg_rgb", [18, 14, 22])
            hover_rgb = self.config.get("custom_hover_rgb", [255, 191, 105])

            accent_hex = f"#{accent_rgb[0]:02x}{accent_rgb[1]:02x}{accent_rgb[2]:02x}"
            bg_hex = f"#{bg_rgb[0]:02x}{bg_rgb[1]:02x}{bg_rgb[2]:02x}"
            hover_hex = f"#{hover_rgb[0]:02x}{hover_rgb[1]:02x}{hover_rgb[2]:02x}"

            if app_mode == "Light":
                card_hex = "#FFFFFF"
                sidebar_hex = "#E8E2EC"
                text_hex = "#1A1420"
            else:
                card_hex = "#1E1724"
                sidebar_hex = "#18121E"
                text_hex = "#FBE8E7"

            self.theme = {
                "bg": bg_hex, "card": card_hex, "sidebar": sidebar_hex,
                "orange": accent_hex, "hover": hover_hex, "gold": accent_hex, "red": "#FF6B6B",
                "text": text_hex
            }
        else:
            base_theme = THEMES.get(theme_name, THEMES["Sunset (Default)"])
            if app_mode == "Light":
                self.theme = {
                    "bg": "#F4F0F5", "card": "#FFFFFF", "sidebar": "#E5DFE9",
                    "orange": base_theme["orange"], "hover": base_theme["hover"],
                    "gold": base_theme["orange"], "red": base_theme["red"], "text": "#1A1420"
                }
            else:
                self.theme = base_theme

    def get_instance_path(self, inst):
        if not inst:
            return self.instances_dir
        path = inst.get("path")
        if not path or path == "None" or not isinstance(path, str):
            name = inst.get("name", "Default")
            path = os.path.join(self.instances_dir, str(name))
            inst["path"] = path
        return path

    def load_config(self):
        config_path = os.path.join(self.base_dir, "jlauncher_config.json")
        default_instance_path = os.path.join(self.instances_dir, "Default Vanilla")
        os.makedirs(default_instance_path, exist_ok=True)
        os.makedirs(os.path.join(default_instance_path, "mods"), exist_ok=True)
        os.makedirs(os.path.join(default_instance_path, "resourcepacks"), exist_ok=True)
        os.makedirs(os.path.join(default_instance_path, "shaderpacks"), exist_ok=True)

        default_config = {
            "username": "",
            "ram": 3,
            "appearance_mode": "Dark",
            "theme": "Sunset (Default)",
            "custom_accent_rgb": [255, 159, 28],
            "custom_bg_rgb": [18, 14, 22],
            "custom_hover_rgb": [255, 191, 105],
            "instances": [
                {
                    "name": "Default Vanilla",
                    "version": self.all_versions[0] if self.all_versions else "1.20.4",
                    "loader": "Vanilla",
                    "path": default_instance_path
                }
            ]
        }

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    if "instances" in data and data["instances"]:
                        for inst in data["instances"]:
                            p = self.get_instance_path(inst)
                            os.makedirs(p, exist_ok=True)
                            os.makedirs(os.path.join(p, "mods"), exist_ok=True)
                            os.makedirs(os.path.join(p, "resourcepacks"), exist_ok=True)
                            os.makedirs(os.path.join(p, "shaderpacks"), exist_ok=True)
                        return data
            except Exception as e:
                print(f"Error loading config: {e}")
        return default_config

    def save_config(self):
        config_path = os.path.join(self.base_dir, "jlauncher_config.json")
        try:
            for inst in self.instances:
                inst["path"] = self.get_instance_path(inst)
            with open(config_path, "w") as f:
                json.dump({
                    "username": self.username_entry.get().strip() if hasattr(self, "username_entry") else self.config.get("username", ""),
                    "ram": int(round(self.ram_slider.get())) if hasattr(self, "ram_slider") else self.config.get("ram", 3),
                    "appearance_mode": self.config.get("appearance_mode", "Dark"),
                    "theme": self.config.get("theme", "Sunset (Default)"),
                    "custom_accent_rgb": self.config.get("custom_accent_rgb", [255, 159, 28]),
                    "custom_bg_rgb": self.config.get("custom_bg_rgb", [18, 14, 22]),
                    "custom_hover_rgb": self.config.get("custom_hover_rgb", [255, 191, 105]),
                    "instances": self.instances
                }, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def setup_ui_layout(self):
        self.sidebar = ctk.CTkFrame(self, width=200, fg_color=self.theme["sidebar"], corner_radius=0)
        self.sidebar.pack(side="left", fill="y")

        self.app_title = ctk.CTkLabel(
            self.sidebar, text="JLAUNCHER", 
            font=ctk.CTkFont(size=16, weight="bold"), text_color=self.theme["orange"]
        )
        self.app_title.pack(pady=(30, 20), padx=16, anchor="w")

        self.nav_play_btn = ctk.CTkButton(
            self.sidebar, text="PLAY & INSTANCES", font=ctk.CTkFont(size=11, weight="bold"),
            height=36, corner_radius=6, fg_color=self.theme["card"], hover_color=self.theme["hover"], text_color=self.theme["text"],
            anchor="w", command=lambda: self.show_page("play")
        )
        self.nav_play_btn.pack(fill="x", padx=12, pady=4)

        self.nav_modrinth_btn = ctk.CTkButton(
            self.sidebar, text="MODRINTH HUB", font=ctk.CTkFont(size=11, weight="bold"),
            height=36, corner_radius=6, fg_color="transparent", hover_color=self.theme["hover"], text_color=self.theme["text"],
            anchor="w", command=lambda: self.show_page("modrinth")
        )
        self.nav_modrinth_btn.pack(fill="x", padx=12, pady=4)

        self.nav_settings_btn = ctk.CTkButton(
            self.sidebar, text="SETTINGS", font=ctk.CTkFont(size=11, weight="bold"),
            height=36, corner_radius=6, fg_color="transparent", hover_color=self.theme["hover"], text_color=self.theme["text"],
            anchor="w", command=lambda: self.show_page("settings")
        )
        self.nav_settings_btn.pack(fill="x", padx=12, pady=4)

        # Made by Jason Mark badge at the bottom of sidebar
        self.credits_lbl = ctk.CTkLabel(
            self.sidebar, text="Made by Jason Mark", 
            font=ctk.CTkFont(size=10, weight="bold"), text_color=self.theme["text"]
        )
        self.credits_lbl.pack(side="bottom", pady=20, padx=16, anchor="w")

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(side="right", fill="both", expand=True, padx=16, pady=16)

        self.page_play = ctk.CTkFrame(self.container, fg_color=self.theme["card"], corner_radius=8, border_width=1, border_color=self.theme["sidebar"])
        self.page_modrinth = ctk.CTkFrame(self.container, fg_color=self.theme["card"], corner_radius=8, border_width=1, border_color=self.theme["sidebar"])
        self.page_settings = ctk.CTkFrame(self.container, fg_color=self.theme["card"], corner_radius=8, border_width=1, border_color=self.theme["sidebar"])

        self.build_play_page()
        self.build_modrinth_page()
        self.build_settings_page()

        self.show_page("play")

    def show_page(self, page_name):
        self.page_play.pack_forget()
        self.page_modrinth.pack_forget()
        self.page_settings.pack_forget()

        self.nav_play_btn.configure(fg_color="transparent")
        self.nav_modrinth_btn.configure(fg_color="transparent")
        self.nav_settings_btn.configure(fg_color="transparent")

        if page_name == "play":
            self.page_play.pack(fill="both", expand=True)
            self.nav_play_btn.configure(fg_color=self.theme["card"])
            self.update_rpc("In Menus", "Viewing the Home Page")
        elif page_name == "modrinth":
            self.page_modrinth.pack(fill="both", expand=True)
            self.nav_modrinth_btn.configure(fg_color=self.theme["card"])
            self.update_rpc("Browsing Hub", "Searching Mods & Shaders")
            self.search_modrinth()
        elif page_name == "settings":
            self.page_settings.pack(fill="both", expand=True)
            self.nav_settings_btn.configure(fg_color=self.theme["card"])
            self.update_rpc("In Settings", "Customizing JLauncher")

    def build_play_page(self):
        # Username Row
        self.user_lbl = ctk.CTkLabel(self.page_play, text="ACCOUNT USERNAME", font=ctk.CTkFont(size=10, weight="bold"), text_color=self.theme["orange"])
        self.user_lbl.pack(anchor="w", padx=35, pady=(30, 4))

        self.username_entry = ctk.CTkEntry(
            self.page_play, placeholder_text="Enter Username", width=420, height=36, corner_radius=6,
            fg_color=self.theme["bg"], border_color=self.theme["orange"], text_color=self.theme["text"]
        )
        self.username_entry.pack(anchor="w", padx=35, pady=(0, 15))
        if self.config.get("username"):
            self.username_entry.insert(0, self.config["username"])

        # Active Instance Row with Action Buttons
        self.instance_label = ctk.CTkLabel(
            self.page_play, text="ACTIVE INSTANCE", font=ctk.CTkFont(size=10, weight="bold"), text_color=self.theme["orange"]
        )
        self.instance_label.pack(anchor="w", padx=35, pady=(4, 4))

        self.instance_frame = ctk.CTkFrame(self.page_play, fg_color="transparent")
        self.instance_frame.pack(anchor="w", padx=35, pady=(0, 15))

        self.instances = self.config.get("instances", [])
        instance_names = [inst["name"] for inst in self.instances]

        self.instance_option = ctk.CTkOptionMenu(
            self.instance_frame, values=instance_names, width=140, height=34, corner_radius=6,
            fg_color=self.theme["bg"], button_color=self.theme["orange"], button_hover_color=self.theme["hover"],
            text_color=self.theme["text"]
        )
        self.instance_option.pack(side="left", padx=(0, 8))
        if instance_names:
            self.instance_option.set(instance_names[0])

        self.add_btn = ctk.CTkButton(
            self.instance_frame, text="+", font=ctk.CTkFont(size=13, weight="bold"),
            width=32, height=34, corner_radius=6, fg_color=self.theme["orange"], hover_color=self.theme["hover"],
            text_color="#141017", command=self.open_add_instance_dialog
        )
        self.add_btn.pack(side="left", padx=(0, 6))

        self.edit_btn = ctk.CTkButton(
            self.instance_frame, text="EDIT", font=ctk.CTkFont(size=10, weight="bold"),
            width=38, height=34, corner_radius=6, fg_color=self.theme["sidebar"], hover_color=self.theme["hover"],
            text_color=self.theme["text"], command=self.open_edit_instance_dialog
        )
        self.edit_btn.pack(side="left", padx=(0, 6))

        self.del_btn = ctk.CTkButton(
            self.instance_frame, text="DEL", font=ctk.CTkFont(size=10, weight="bold"),
            width=34, height=34, corner_radius=6, fg_color=self.theme["sidebar"], hover_color=self.theme["red"],
            text_color=self.theme["text"], command=self.open_delete_dialog
        )
        self.del_btn.pack(side="left", padx=(0, 6))

        self.folder_btn = ctk.CTkButton(
            self.instance_frame, text="OPEN", font=ctk.CTkFont(size=10, weight="bold"),
            width=38, height=34, corner_radius=6, fg_color=self.theme["sidebar"], hover_color=self.theme["hover"],
            text_color=self.theme["text"], command=self.open_instance_folder
        )
        self.folder_btn.pack(side="left", padx=(0, 6))

        self.logs_btn = ctk.CTkButton(
            self.instance_frame, text="LOGS", font=ctk.CTkFont(size=10, weight="bold"),
            width=38, height=34, corner_radius=6, fg_color=self.theme["sidebar"], hover_color=self.theme["gold"],
            text_color=self.theme["text"], command=self.open_logs_folder
        )
        self.logs_btn.pack(side="left", padx=(0, 6))

        self.manage_btn = ctk.CTkButton(
            self.instance_frame, text="MANAGE", font=ctk.CTkFont(size=10, weight="bold"),
            width=50, height=34, corner_radius=6, fg_color=self.theme["sidebar"], hover_color=self.theme["orange"],
            text_color=self.theme["text"], command=self.open_manage_content_dialog
        )
        self.manage_btn.pack(side="left")

        # Allocated Memory Label
        saved_ram = self.config.get("ram", 3)
        self.ram_label = ctk.CTkLabel(
            self.page_play, text=f"ALLOCATED MEMORY: {saved_ram} GB", 
            font=ctk.CTkFont(size=10, weight="bold"), text_color=self.theme["orange"]
        )
        self.ram_label.pack(anchor="w", padx=35, pady=(4, 4))

        # RAM Slider & Preset Buttons Row
        slider_row = ctk.CTkFrame(self.page_play, fg_color="transparent")
        slider_row.pack(anchor="w", padx=35, pady=(0, 25), fill="x")

        self.ram_slider = ctk.CTkSlider(
            slider_row, from_=1, to=8, number_of_steps=7, width=290,
            progress_color=self.theme["orange"], button_color=self.theme["hover"], button_hover_color="#FFF",
            command=self.update_ram_label
        )
        self.ram_slider.set(saved_ram)
        self.ram_slider.pack(side="left", pady=4)

        preset_frame = ctk.CTkFrame(slider_row, fg_color="transparent")
        preset_frame.pack(side="left", padx=(12, 0))
        
        for gb in [2, 4, 6]:
            btn = ctk.CTkButton(
                preset_frame, text=f"{gb}G", font=ctk.CTkFont(size=10, weight="bold"),
                width=34, height=28, corner_radius=6, fg_color=self.theme["sidebar"], hover_color=self.theme["orange"],
                text_color=self.theme["text"], command=lambda val=gb: self.set_ram_preset(val)
            )
            btn.pack(side="left", padx=3)

        # Play Button
        self.launch_button = ctk.CTkButton(
            self.page_play, text="PLAY GAME", font=ctk.CTkFont(size=13, weight="bold"),
            width=420, height=40, corner_radius=6, fg_color=self.theme["orange"], hover_color=self.theme["hover"],
            text_color="#141017", command=self.start_launch_thread
        )
        self.launch_button.pack(anchor="w", padx=35, pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(
            self.page_play, width=420, height=6, corner_radius=3,
            progress_color=self.theme["orange"], fg_color=self.theme["bg"]
        )
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(
            self.page_play, text="", text_color=self.theme["text"], font=ctk.CTkFont(size=11)
        )

    def open_logs_folder(self):
        instance = self.get_selected_instance()
        if instance:
            path = os.path.join(self.get_instance_path(instance), "logs")
            os.makedirs(path, exist_ok=True)
            subprocess.run(["open", path])

    def set_ram_preset(self, gb):
        self.ram_slider.set(gb)
        self.update_ram_label(gb)

    def build_settings_page(self):
        settings_title = ctk.CTkLabel(
            self.page_settings, text="LAUNCHER SETTINGS", 
            font=ctk.CTkFont(size=14, weight="bold"), text_color=self.theme["orange"]
        )
        settings_title.pack(anchor="w", padx=25, pady=(20, 15))

        self.settings_scroll = ctk.CTkScrollableFrame(
            self.page_settings, fg_color=self.theme["bg"], corner_radius=8
        )
        self.settings_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # --- APPEARANCE MODE ---
        mode_header = ctk.CTkLabel(
            self.settings_scroll, text="APPEARANCE MODE", 
            font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme["orange"], anchor="w"
        )
        mode_header.pack(fill="x", padx=15, pady=(12, 6))

        mode_frame = ctk.CTkFrame(self.settings_scroll, fg_color="transparent")
        mode_frame.pack(fill="x", padx=15, pady=4)

        ctk.CTkLabel(mode_frame, text="Interface Brightness:", font=ctk.CTkFont(size=11), text_color=self.theme["text"]).pack(side="left", padx=(0, 15))

        self.mode_option = ctk.CTkOptionMenu(
            mode_frame, values=["Dark", "Light"], width=160, height=34, corner_radius=6,
            fg_color=self.theme["card"], button_color=self.theme["orange"], button_hover_color=self.theme["hover"],
            text_color=self.theme["text"], command=self.on_appearance_mode_change
        )
        self.mode_option.pack(side="left")
        self.mode_option.set(self.config.get("appearance_mode", "Dark"))

        # --- THEME PRESETS ---
        vis_header = ctk.CTkLabel(
            self.settings_scroll, text="THEME PRESETS", 
            font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme["orange"], anchor="w"
        )
        vis_header.pack(fill="x", padx=15, pady=(16, 6))

        preset_frame = ctk.CTkFrame(self.settings_scroll, fg_color="transparent")
        preset_frame.pack(fill="x", padx=15, pady=4)

        ctk.CTkLabel(preset_frame, text="Color Palette:", font=ctk.CTkFont(size=11), text_color=self.theme["text"]).pack(side="left", padx=(0, 15))

        theme_choices = list(THEMES.keys()) + ["Custom Customization"]
        self.settings_theme_option = ctk.CTkOptionMenu(
            preset_frame, values=theme_choices, width=200, height=34, corner_radius=6,
            fg_color=self.theme["card"], button_color=self.theme["orange"], button_hover_color=self.theme["hover"],
            text_color=self.theme["text"], command=self.on_theme_preset_changed
        )
        self.settings_theme_option.pack(side="left")
        self.settings_theme_option.set(self.config.get("theme", "Sunset (Default)"))

        # --- RGB COLOR SLIDERS CARD ---
        rgb_card = ctk.CTkFrame(self.settings_scroll, fg_color=self.theme["card"], corner_radius=8, border_width=1, border_color=self.theme["sidebar"])
        rgb_card.pack(fill="x", padx=15, pady=16)

        rgb_title = ctk.CTkLabel(rgb_card, text="CUSTOM ACCENT & BACKGROUND SLIDERS", font=ctk.CTkFont(size=11, weight="bold"), text_color=self.theme["orange"], anchor="w")
        rgb_title.pack(fill="x", padx=15, pady=(12, 10))

        custom_accent = self.config.get("custom_accent_rgb", [255, 159, 28])
        custom_bg = self.config.get("custom_bg_rgb", [18, 14, 22])
        custom_hover = self.config.get("custom_hover_rgb", [255, 191, 105])

        # 1. ACCENT COLOR SLIDER
        ctk.CTkLabel(rgb_card, text="1. Accent Color", font=ctk.CTkFont(size=10, weight="bold"), text_color=self.theme["text"], anchor="w").pack(fill="x", padx=15, pady=(4, 2))
        self.acc_r = self._build_single_slider(rgb_card, "R", custom_accent[0], "#FF6B6B")
        self.acc_g = self._build_single_slider(rgb_card, "G", custom_accent[1], "#2ECC71")
        self.acc_b = self._build_single_slider(rgb_card, "B", custom_accent[2], "#3498DB")

        # 2. BACKGROUND COLOR SLIDER
        ctk.CTkLabel(rgb_card, text="2. Background Color", font=ctk.CTkFont(size=10, weight="bold"), text_color=self.theme["text"], anchor="w").pack(fill="x", padx=15, pady=(10, 2))
        self.bg_r = self._build_single_slider(rgb_card, "R", custom_bg[0], "#FF6B6B")
        self.bg_g = self._build_single_slider(rgb_card, "G", custom_bg[1], "#2ECC71")
        self.bg_b = self._build_single_slider(rgb_card, "B", custom_bg[2], "#3498DB")

        # 3. HOVER COLOR SLIDER
        ctk.CTkLabel(rgb_card, text="3. Hover Color", font=ctk.CTkFont(size=10, weight="bold"), text_color=self.theme["text"], anchor="w").pack(fill="x", padx=15, pady=(10, 2))
        self.hov_r = self._build_single_slider(rgb_card, "R", custom_hover[0], "#FF6B6B")
        self.hov_g = self._build_single_slider(rgb_card, "G", custom_hover[1], "#2ECC71")
        self.hov_b = self._build_single_slider(rgb_card, "B", custom_hover[2], "#3498DB")

        # PREVIEW BOXES & APPLY BUTTON
        preview_frame = ctk.CTkFrame(rgb_card, fg_color="transparent")
        preview_frame.pack(fill="x", padx=15, pady=(15, 15))

        ctk.CTkLabel(preview_frame, text="Preview:", font=ctk.CTkFont(size=11), text_color=self.theme["text"]).pack(side="left", padx=(0, 8))

        self.preview_acc_box = ctk.CTkFrame(preview_frame, width=28, height=28, fg_color=self.theme["orange"], corner_radius=4)
        self.preview_acc_box.pack(side="left", padx=4)

        self.preview_bg_box = ctk.CTkFrame(preview_frame, width=28, height=28, fg_color=self.theme["bg"], corner_radius=4)
        self.preview_bg_box.pack(side="left", padx=4)

        self.preview_hov_box = ctk.CTkFrame(preview_frame, width=28, height=28, fg_color=self.theme["hover"], corner_radius=4)
        self.preview_hov_box.pack(side="left", padx=4)

        apply_custom_btn = ctk.CTkButton(
            preview_frame, text="APPLY COLORS", font=ctk.CTkFont(size=11, weight="bold"),
            height=32, corner_radius=6, fg_color=self.theme["orange"], hover_color=self.theme["hover"],
            text_color="#141017", command=self.apply_custom_rgb_theme
        )
        apply_custom_btn.pack(side="right", padx=(15, 0))

    def _build_single_slider(self, parent, label_text, default_val, bar_color):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(frame, text=label_text, font=ctk.CTkFont(size=10, weight="bold"), text_color=bar_color, width=20, anchor="w").pack(side="left")
        
        slider = ctk.CTkSlider(frame, from_=0, to=255, number_of_steps=255, width=210, progress_color=bar_color, command=lambda v: self._update_live_previews())
        slider.set(default_val)
        slider.pack(side="left", padx=8)

        val_lbl = ctk.CTkLabel(frame, text=str(default_val), font=ctk.CTkFont(size=10), text_color=self.theme["text"], width=25)
        val_lbl.pack(side="left")
        slider.val_lbl = val_lbl
        return slider

    def _update_live_previews(self):
        acc_r, acc_g, acc_b = int(round(self.acc_r.get())), int(round(self.acc_g.get())), int(round(self.acc_b.get()))
        bg_r, bg_g, bg_b = int(round(self.bg_r.get())), int(round(self.bg_g.get())), int(round(self.bg_b.get()))
        hov_r, hov_g, hov_b = int(round(self.hov_r.get())), int(round(self.hov_g.get())), int(round(self.hov_b.get()))

        self.acc_r.val_lbl.configure(text=str(acc_r))
        self.acc_g.val_lbl.configure(text=str(acc_g))
        self.acc_b.val_lbl.configure(text=str(acc_b))

        self.bg_r.val_lbl.configure(text=str(bg_r))
        self.bg_g.val_lbl.configure(text=str(bg_g))
        self.bg_b.val_lbl.configure(text=str(bg_b))

        self.hov_r.val_lbl.configure(text=str(hov_r))
        self.hov_g.val_lbl.configure(text=str(hov_g))
        self.hov_b.val_lbl.configure(text=str(hov_b))

        self.preview_acc_box.configure(fg_color=f"#{acc_r:02x}{acc_g:02x}{acc_b:02x}")
        self.preview_bg_box.configure(fg_color=f"#{bg_r:02x}{bg_g:02x}{bg_b:02x}")
        self.preview_hov_box.configure(fg_color=f"#{hov_r:02x}{hov_g:02x}{hov_b:02x}")

    def on_appearance_mode_change(self, mode):
        self.config["appearance_mode"] = mode
        ctk.set_appearance_mode(mode)
        self.save_config()
        self.restart_app()

    def on_theme_preset_changed(self, preset_name):
        self.config["theme"] = preset_name
        self.save_config()
        self.restart_app()

    def apply_custom_rgb_theme(self):
        self.config["theme"] = "Custom Customization"
        self.config["custom_accent_rgb"] = [int(round(self.acc_r.get())), int(round(self.acc_g.get())), int(round(self.acc_b.get()))]
        self.config["custom_bg_rgb"] = [int(round(self.bg_r.get())), int(round(self.bg_g.get())), int(round(self.bg_b.get()))]
        self.config["custom_hover_rgb"] = [int(round(self.hov_r.get())), int(round(self.hov_g.get())), int(round(self.hov_b.get()))]
        self.save_config()
        self.restart_app()

    def restart_app(self):
        self.destroy()
        import sys
        os.execl(sys.executable, sys.executable, *sys.argv)

    def build_modrinth_page(self):
        cat_frame = ctk.CTkFrame(self.page_modrinth, fg_color="transparent")
        cat_frame.pack(fill="x", padx=16, pady=(16, 8))

        self.cat_buttons = {}
        categories = [("MODS", "mod"), ("RESOURCE PACKS", "resourcepack"), ("SHADERS", "shader")]
        
        for text, p_type in categories:
            is_active = (p_type == self.current_project_type)
            btn = ctk.CTkButton(
                cat_frame, text=text, font=ctk.CTkFont(size=11, weight="bold"),
                width=120, height=34, corner_radius=6, fg_color=self.theme["orange"] if is_active else self.theme["card"],
                hover_color=self.theme["hover"], text_color="#141017" if is_active else self.theme["text"],
                command=lambda pt=p_type: self.set_modrinth_category(pt)
            )
            btn.pack(side="left", padx=(0, 8))
            self.cat_buttons[p_type] = btn

        search_frame = ctk.CTkFrame(self.page_modrinth, fg_color="transparent")
        search_frame.pack(fill="x", padx=16, pady=(8, 12))

        self.mod_search_entry = ctk.CTkEntry(
            search_frame, placeholder_text="Search Modrinth...", 
            height=36, corner_radius=6, fg_color=self.theme["bg"], border_color=self.theme["orange"], text_color=self.theme["text"]
        )
        self.mod_search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.mod_search_btn = ctk.CTkButton(
            search_frame, text="SEARCH", font=ctk.CTkFont(size=11, weight="bold"),
            width=90, height=36, corner_radius=6, fg_color=self.theme["orange"], hover_color=self.theme["hover"],
            text_color="#141017", command=self.search_modrinth
        )
        self.mod_search_btn.pack(side="right")

        self.mod_scroll_frame = ctk.CTkScrollableFrame(
            self.page_modrinth, fg_color=self.theme["bg"], corner_radius=8
        )
        self.mod_scroll_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def set_modrinth_category(self, p_type):
        self.current_project_type = p_type
        for pt, btn in self.cat_buttons.items():
            if pt == p_type:
                btn.configure(fg_color=self.theme["orange"], text_color="#141017")
            else:
                btn.configure(fg_color=self.theme["card"], text_color=self.theme["text"])
        self.search_modrinth()

    def search_modrinth(self):
        query = self.mod_search_entry.get().strip()
        
        for widget in self.mod_scroll_frame.winfo_children():
            widget.destroy()

        loading_lbl = ctk.CTkLabel(self.mod_scroll_frame, text="Searching Modrinth...", text_color=self.theme["gold"])
        loading_lbl.pack(pady=20)

        threading.Thread(target=self._fetch_modrinth_data, args=(query,), daemon=True).start()

    def _fetch_modrinth_data(self, query):
        try:
            encoded_q = urllib.parse.quote(query)
            facets = json.dumps([[f"project_type:{self.current_project_type}"]])
            url = f"https://api.modrinth.com/v2/search?query={encoded_q}&facets={urllib.parse.quote(facets)}&limit=12"
            
            response = requests.get(url, headers={'User-Agent': 'JLauncher/1.0'}, verify=False)
            data = response.json()
            results = data.get("hits", [])

            self.after(0, lambda: self._populate_mod_results(results))
        except Exception as e:
            print(f"Modrinth API Error: {e}")
            self.after(0, lambda: self._populate_mod_results([]))

    def _populate_mod_results(self, results):
        for widget in self.mod_scroll_frame.winfo_children():
            widget.destroy()

        if not results:
            empty_lbl = ctk.CTkLabel(self.mod_scroll_frame, text="No items found. Try a different search term.", text_color=self.theme["text"])
            empty_lbl.pack(pady=30)
            return

        for mod in results:
            title = mod.get("title", "Unknown")
            description = mod.get("description", "No description available.")
            project_id = mod.get("project_id")
            downloads = mod.get("downloads", 0)

            card = ctk.CTkFrame(self.mod_scroll_frame, fg_color=self.theme["card"], corner_radius=6, border_width=1, border_color=self.theme["sidebar"])
            card.pack(fill="x", padx=8, pady=5)

            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=12, pady=10)

            mod_title = ctk.CTkLabel(info_frame, text=f"{title}  ({downloads:,} downloads)", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme["gold"], anchor="w")
            mod_title.pack(fill="x")

            mod_desc = ctk.CTkLabel(info_frame, text=description[:85] + ("..." if len(description) > 85 else ""), font=ctk.CTkFont(size=11), text_color=self.theme["text"], anchor="w")
            mod_desc.pack(fill="x", pady=(2, 0))

            install_btn = ctk.CTkButton(
                card, text="INSTALL", font=ctk.CTkFont(size=11, weight="bold"),
                width=85, height=32, corner_radius=6, fg_color=self.theme["orange"], hover_color=self.theme["hover"],
                text_color="#141017", command=lambda p_id=project_id, t=title: self.prompt_install_mod(p_id, t)
            )
            install_btn.pack(side="right", padx=12, pady=10)

    def prompt_install_mod(self, project_id, mod_title):
        SelectInstanceDialog(self, self.instances, self.current_project_type, self.theme, lambda target_inst: self.install_mod_to_instance(project_id, target_inst, mod_title))

    def install_mod_to_instance(self, project_id, target_instance, mod_title):
        threading.Thread(target=self._download_mod_file, args=(project_id, target_instance, mod_title), daemon=True).start()

    def _download_mod_file(self, project_id, instance, mod_title):
        try:
            instance_path = self.get_instance_path(instance)
            inst_ver = instance.get("version", "1.20.4")
            inst_loader = instance.get("loader", "Fabric").lower()

            url = f"https://api.modrinth.com/v2/project/{project_id}/version"
            response = requests.get(url, headers={'User-Agent': 'JLauncher/1.0'}, verify=False)
            versions_data = response.json()
            
            if isinstance(versions_data, list) and versions_data:
                target_v_data = None
                for v in versions_data:
                    game_vers = v.get("game_versions", [])
                    loaders = [l.lower() for l in v.get("loaders", [])]
                    if inst_ver in game_vers:
                        if self.current_project_type != "mod" or (not inst_loader or "fabric" in inst_loader and "fabric" in loaders or "forge" in inst_loader and ("forge" in loaders or "neoforge" in loaders)):
                            target_v_data = v
                            break
                
                if not target_v_data:
                    target_v_data = versions_data[0]

                files = target_v_data.get("files", [])
                if files:
                    download_url = files[0].get("url")
                    filename = files[0].get("filename")

                    if self.current_project_type == "resourcepack":
                        subfolder = "resourcepacks"
                    elif self.current_project_type == "shader":
                        subfolder = "shaderpacks"
                    else:
                        subfolder = "mods"

                    dest_folder = os.path.join(instance_path, subfolder)
                    os.makedirs(dest_folder, exist_ok=True)
                    dest_path = os.path.join(dest_folder, filename)

                    res_file = requests.get(download_url, headers={'User-Agent': 'JLauncher/1.0'}, verify=False, stream=True)
                    with open(dest_path, 'wb') as out_file:
                        for chunk in res_file.iter_content(chunk_size=8192):
                            out_file.write(chunk)

                    print(f"Successfully installed {filename} into {instance['name']}/{subfolder}/")
        except Exception as e:
            print(f"Error downloading file: {e}")

    def open_add_instance_dialog(self):
        AddInstanceDialog(self, self.all_versions, self.theme, self.add_new_instance)

    def add_new_instance(self, name, version, loader):
        if any(inst["name"] == name for inst in self.instances):
            return

        instance_path = os.path.join(self.instances_dir, name)
        os.makedirs(instance_path, exist_ok=True)
        os.makedirs(os.path.join(instance_path, "mods"), exist_ok=True)
        os.makedirs(os.path.join(instance_path, "resourcepacks"), exist_ok=True)
        os.makedirs(os.path.join(instance_path, "shaderpacks"), exist_ok=True)

        new_instance = {"name": name, "version": version, "loader": loader, "path": instance_path}
        self.instances.append(new_instance)
        
        instance_names = [inst["name"] for inst in self.instances]
        self.instance_option.configure(values=instance_names)
        self.instance_option.set(name)

        self.save_config()

    def open_edit_instance_dialog(self):
        current_instance = self.get_selected_instance()
        if current_instance:
            EditInstanceDialog(self, current_instance, self.all_versions, self.theme, self.update_instance)

    def update_instance(self, old_name, new_name, new_version, new_loader):
        if old_name != new_name and any(inst["name"] == new_name for inst in self.instances):
            return

        for inst in self.instances:
            if inst["name"] == old_name:
                old_path = self.get_instance_path(inst)
                new_path = os.path.join(self.instances_dir, new_name)
                
                if old_path != new_path:
                    if os.path.exists(old_path):
                        os.rename(old_path, new_path)
                    else:
                        os.makedirs(new_path, exist_ok=True)
                
                inst["name"] = new_name
                inst["version"] = new_version
                inst["loader"] = new_loader
                inst["path"] = new_path
                break

        instance_names = [inst["name"] for inst in self.instances]
        self.instance_option.configure(values=instance_names)
        self.instance_option.set(new_name)
        self.save_config()

    def open_delete_dialog(self):
        current_instance = self.get_selected_instance()
        if current_instance and len(self.instances) > 1:
            try:
                path = self.get_instance_path(current_instance)
                if os.path.exists(path):
                    shutil.rmtree(path)
            except Exception as e:
                print(f"Error removing instance folder: {e}")

            self.instances = [inst for inst in self.instances if inst["name"] != current_instance["name"]]
            
            instance_names = [inst["name"] for inst in self.instances]
            self.instance_option.configure(values=instance_names)
            self.instance_option.set(instance_names[0])

            self.save_config()

    def open_instance_folder(self):
        instance = self.get_selected_instance()
        if instance:
            path = self.get_instance_path(instance)
            if os.path.exists(path):
                subprocess.run(["open", path])

    def open_manage_content_dialog(self):
        instance = self.get_selected_instance()
        if instance:
            ManageContentDialog(self, instance, self.theme)

    def update_ram_label(self, value):
        ram_val = int(round(value))
        self.ram_label.configure(text=f"ALLOCATED MEMORY: {ram_val} GB")

    def get_vanilla_versions(self):
        try:
            all_versions = minecraft_launcher_lib.utils.get_version_list()
            releases = [v["id"] for v in all_versions if v["type"] == "release"][::-1]
            return releases
        except Exception as e:
            print(f"Error fetching versions: {e}")
            return ["1.20.4", "1.20.1", "1.16.5"]

    def set_status(self, text):
        self.after(0, lambda: self.status_label.configure(text=text, text_color=self.theme["gold"]))

    def set_progress(self, current):
        if self.max_progress > 0:
            fraction = current / self.max_progress
            percentage = int(fraction * 100)
            self.after(0, lambda: (
                self.progress_bar.set(fraction),
                self.status_label.configure(
                    text=f"Downloading: {percentage}% ({current}/{self.max_progress} files)"
                )
            ))

    def set_max_progress(self, max_val):
        self.max_progress = max_val

    def get_selected_instance(self):
        selected_name = self.instance_option.get()
        for inst in self.instances:
            if inst["name"] == selected_name:
                self.get_instance_path(inst)
                return inst
        return self.instances[0] if self.instances else None

    def start_launch_thread(self):
        username = self.username_entry.get().strip()
        if not username:
            return

        instance = self.get_selected_instance()
        if not instance:
            return

        ram_val = int(round(self.ram_slider.get()))
        self.save_config()

        self.progress_bar.pack(anchor="w", padx=35, pady=(12, 4))
        self.status_label.pack(anchor="w", padx=35, pady=(0, 10))
        self.progress_bar.set(0)
        self.status_label.configure(text=f"Preparing '{instance['name']}' ({instance.get('loader', 'Vanilla')})...", text_color=self.theme["gold"])

        self.launch_button.configure(
            text="STOP GAME", fg_color=self.theme["red"], hover_color="#D9534F",
            command=self.stop_game
        )

        path = self.get_instance_path(instance)

        # Update Discord Rich Presence to Playing Game
        self.update_rpc(f"Playing {instance['name']}", "Singleplayer / Server")

        threading.Thread(
            target=self.launch_game,
            args=(username, instance["version"], instance.get("loader", "Vanilla"), path, ram_val),
            daemon=True
        ).start()

    def stop_game(self):
        instance = self.get_selected_instance()
        if instance:
            try:
                path = self.get_instance_path(instance)
                folder_name = os.path.basename(path)
                subprocess.run(["pkill", "-9", "-f", path], capture_output=True)
                subprocess.run(["pkill", "-9", "-f", folder_name], capture_output=True)
            except Exception as e:
                print(f"Error terminating process: {e}")
        
        self.update_rpc("In Menus", "Viewing the Home Page")
        self.reset_ui_to_play()

    def launch_game(self, username, version, loader, instance_path, ram_val):
        try:
            callback = {
                "setStatus": self.set_status,
                "setProgress": self.set_progress,
                "setMax": self.set_max_progress
            }

            if loader == "Fabric":
                self.set_status("Installing Fabric Loader...")
                minecraft_launcher_lib.fabric.install_fabric(version, instance_path, callback=callback)
                
                version_to_launch = version
                installed_versions = minecraft_launcher_lib.utils.get_installed_versions(instance_path)
                for v in installed_versions:
                    v_id = v.get("id", "")
                    if "fabric" in v_id.lower() and version in v_id:
                        version_to_launch = v_id
                        break
                else:
                    for v in installed_versions:
                        if "fabric" in v.get("id", "").lower():
                            version_to_launch = v.get("id")
                            break
            else:
                minecraft_launcher_lib.install.install_minecraft_version(version, instance_path, callback=callback)
                version_to_launch = version

            if not version_to_launch:
                version_to_launch = version

            if self.launch_button.cget("text") == "PLAY GAME":
                return

            self.after(0, lambda: self.progress_bar.set(1.0))
            self.set_status("Game is running!")

            options = {
                "username": username,
                "uuid": "",
                "token": "",
                "jvmArguments": [f"-Xmx{ram_val}G", "-Xms1G"]
            }

            launch_command = minecraft_launcher_lib.command.get_minecraft_command(
                version_to_launch, instance_path, options
            )

            print("Launching with command:", launch_command)
            subprocess.Popen(launch_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        except Exception as e:
            print(f"Launch/Network Exception: {e}")
            self.set_status("Network Error: Check internet connection!")
            self.update_rpc("In Menus", "Viewing the Home Page")
            self.after(4000, self.reset_ui_to_play)

    def reset_ui_to_play(self):
        self.progress_bar.pack_forget()
        self.status_label.pack_forget()
        self.launch_button.configure(
            text="PLAY GAME", fg_color=self.theme["orange"], hover_color=self.theme["hover"],
            command=self.start_launch_thread, state="normal"
        )


if __name__ == "__main__":
    import sys
    app = MinecraftLauncher()
    app.mainloop()