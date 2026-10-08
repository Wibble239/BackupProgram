import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askdirectory
import json
import os
import threading
import shutil
from datetime import datetime
import ctypes
import re

class BackupGUI:
    def __init__(self, root, location, folders):
        self.root = root            #
        self.location = location    # Loading data and window into the class
        self.folders = folders      #

        self.failed = []            # List to track failed transfers

        self.window = ttk.Frame(root, padding="10", style="TFrame")                                                                                             #
        self.window.grid(row=0, column=0, sticky=(tk.W, tk.E))                                                                                                  #
        self.buttons_frame = ttk.Frame(self.window, padding="10", style="TFrame")                                                                               #
        self.buttons_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))                                                                                           #
        self.display_frame = ttk.Frame(self.window, padding="10", style="TFrame")                                                                               #
        self.display_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))                                                                                           #
        self.location_button = ttk.Button(self.buttons_frame, text="Change Backup Location", command=self.set_location)                                         #
        self.location_button.grid(row=0, column=0, padx=5)                                                                                                      # Building the GUI
        self.add_button = ttk.Button(self.buttons_frame, text="Add Folder", command=self.add_folder)                                                            # Using grid for layout and threading to keep UI responsive
        self.add_button.grid(row=0, column=1, padx=5)                                                                                                           #
        self.save_button = ttk.Button(self.buttons_frame, text="Save Changes", command=self.save_to_json)                                                       #
        self.save_button.grid(row=0, column=2, padx=5)                                                                                                          #
        self.start_button = ttk.Button(self.buttons_frame, text="Start Backup", command=(lambda: threading.Thread(target=self.check_storage_space).start()))    #
        self.start_button.grid(row=0, column=3, padx=5)                                                                                                         #
        self.window.columnconfigure(0, weight=1)                                                                                                                #
        self.display_frame.columnconfigure(0, weight=1)                                                                                                         #
        
        self.draw_config()

    def draw_config(self):  # Draws the configuration display by destroying and recreating widgets
        for widget in self.display_frame.winfo_children():
            widget.destroy()
        ttk.Label(self.display_frame, text="Backup Location: ", style="TLabel").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(self.display_frame, text=f"{self.location}", style="TLabel").grid(row=0, column=1, sticky=tk.W)

        span = max(1, len(self.folders))

        ttk.Label(self.display_frame, text="Folders to Backup: ", style="TLabel").grid(row=1, column=0, rowspan=span, sticky=tk.W)
        for i in range(len(self.folders)):
            ttk.Label(self.display_frame, text=f"{self.folders[i]}", style="TLabel").grid(row=i+1, column=1, sticky=tk.W)
            ttk.Button(self.display_frame, text="Remove", command=lambda f=self.folders[i]: self.remove_folder(f)).grid(row=i+1, column=2)

    def draw_progress(self, progress, text):    # Draws or updates the progress bar and label
        if hasattr(self, 'progress_bar'):   # Checking if progress bar already exists to determine whether to create or update
            self.progress_bar["value"] = progress
            self.progress_label.config(text=text)
        else:   # Clears the window and creates new progress bar and label if it didnt exist
            for widget in self.display_frame.winfo_children():
                widget.destroy()
            self.progress_label = ttk.Label(self.display_frame, text=text, style="TLabel", font=("Arial", 8), width=90)
            self.progress_label.grid(row=0, column=0, sticky=tk.W)
            self.progress_bar = ttk.Progressbar(self.display_frame, mode="determinate", maximum=100)
            self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
            self.progress_bar["value"] = progress

    def sub_window(self, message):  # Creates a sub window for important messages
        sub_win = tk.Toplevel(self.root)
        sub_win.resizable(0, 0)
        root.eval(f'tk::PlaceWindow {str(sub_win)} center')
        sub_frame = ttk.Frame(sub_win, padding="10", style="TFrame")
        sub_frame.grid(row=0, column=0)
        ttk.Label(sub_frame, text=message, style="TLabel").grid(row=0, column=0, padx=20, pady=20)

        def on_ok():
            sub_win.destroy()
            if hasattr(self, 'progress_bar'):
                del self.progress_bar
            if hasattr(self, 'progress_label'):
                del self.progress_label
            self.draw_config()

        ttk.Button(sub_frame, text="OK", command=on_ok).grid(row=1, column=0, padx=20, pady=20)
        
    def save_to_json(self): # Saves current configuration to a json file
        script_dir = os.path.dirname(__file__)
        config_dir = os.path.join(script_dir, 'data')
        os.makedirs(config_dir, exist_ok=True)
        file_path = os.path.join(config_dir, 'backup_config.json')
        
        data = {
            "location": self.location,
            "folders": self.folders
        }
        with open(file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)

        self.sub_window("Changes Saved Successfully")

    @classmethod
    def load_from_json(cls, root):  # Loads configuration from a json file, class method to allow it to create an instance
        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, 'data', 'backup_config.json')
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
            return cls(
                root=root,
                location=data.get("location"),
                folders=data.get("folders", [])
            )
        
    def add_folder(self):   # Opens a dialog to add a folder to the backup list
        folder = askdirectory()
        if folder:
            self.folders.append(folder)
            self.draw_config()

    def remove_folder(self, folder): # Removes a folder from the backup list
        if folder in self.folders:
            self.folders.remove(folder)
            self.draw_config()

    def set_location(self): # Opens a dialog to set the backup location
        location = askdirectory()
        if location:
            self.location = location
            self.draw_config()

    def start_backup(self): # Creates the required directories, calls the custom copy tree function and calls to draw the completed progress
        self.file_copied = 0
        backup_folder = f"{self.location}/Backup_{datetime.now().strftime('%Y%m%d')}"
        os.makedirs(backup_folder, exist_ok=True)
        for folder in self.folders:
            self.current_folder = folder
            dest = os.path.join(backup_folder, os.path.basename(folder))
            self.custom_copytree(folder, dest)
        if self.failed:
            with open(os.path.join(backup_folder, "failed_transfers.txt"), 'w') as f:
                for item in self.failed:
                    f.write(f"{item}\n")
            self.root.after(0, lambda: self.sub_window(f"{len(self.failed)} files failed to transfer. See failed_transfers.txt in the backup folder for details."))
        self.root.after(0, lambda: self.draw_progress(100, "Backup Complete"))
        self.root.after(0, lambda: self.sub_window("Backup Complete!"))

    def check_storage_space(self):  # Calculates the size of the backup (ignoring hidden files) and compares it to the space available at the backup location
        self.root.after(0, lambda: self.draw_progress(0, "Calculating Backup Size..."))
        total_size = 0
        self.file_count = 0
        for folder in self.folders:
            for dirpath, dirnames, filenames in os.walk(folder):
                dirnames[:] = [d for d in dirnames if not self.is_hidden(os.path.join(dirpath, d))]
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if self.is_hidden(fp):
                        continue
                    total_size += os.path.getsize(fp)
                    self.root.after(0, lambda: self.draw_progress(0, f"Calculating Backup Size... {total_size / (1024*1024*1024):.2f} GB"))
                    self.file_count += 1

        if shutil.disk_usage(self.location).free > total_size:
            self.start_backup()
        else:
            self.root.after(0, lambda: self.sub_window("Not enough storage space for backup."))

    def custom_copytree(self, src, dst):    # Custom recursive copy function as copytree does not allow tracking progress
        os.makedirs(dst, exist_ok=True)
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(src))
            if attrs != -1:
                ctypes.windll.kernel32.SetFileAttributesW(str(dst), attrs)  # Copy hidden/system attributes
        except Exception:
            pass  # Fallback: ignore if attribute copy fails
        names = os.listdir(src)
        
        for name in names:
            srcname = os.path.join(src, name)
            if self.is_hidden(srcname):
                continue  # Skip hidden files or dirs
            
            dstname = os.path.join(dst, name)
            if os.path.isdir(srcname):
                self.custom_copytree(srcname, dstname)
            else:
                short_name = re.split(r'[\\/]', srcname)
                progress_name_start = (short_name[0] + "/.../" + os.path.basename(self.current_folder))[:45] + "/.../"
                progress_name = progress_name_start + short_name[-1][-(85-len(progress_name_start)):]
                self.root.after(0, lambda n=name: self.draw_progress((self.file_copied / self.file_count) * 100, f"Copying {progress_name}"))
                try:
                    shutil.copy2(srcname, dstname)
                except:
                    self.failed.append(srcname)
                self.file_copied += 1

    def is_hidden(self, filepath):  # Checks if a file or directory is hidden (Windows only)
        if os.path.basename(filepath) == ".git":
            return False  # Allows .git folders to be copied
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(filepath))
            if attrs == -1:
                return False
            return (attrs & 2)
        except Exception:
            return False  # Fallback if any issue

root = tk.Tk()
root.title("Backup")
script_dir = os.path.dirname(__file__)
icon_path = os.path.join(script_dir, 'data', 'icon.ico')
root.wm_iconbitmap(icon_path)
root.resizable(0, 0)
root.eval('tk::PlaceWindow . center')

s = ttk.Style()                                                                             #
s.configure("TFrame", background="#202020", borderwidth=1, relief="solid")                # Setting style for
s.configure("TLabel", background="#202020", foreground="#FFFFFF", font=("Arial", 12))   # buttons labels and frames
s.configure("TButton", background="#202020", foreground="#000000", font=("Arial", 12))  #

try:
    app = BackupGUI.load_from_json(root)
except FileNotFoundError:
    app = BackupGUI(root, location="", folders=[])

root.mainloop()