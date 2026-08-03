import sys
import traceback
from tkinter import *
from tkinter import font as FNT
from tkinter import filedialog as fd
from tkinter import ttk
import tkinter as TKIN
from gui import main_window
from collections import Counter
from PIL import Image, ImageTk
from logic import checksum as checksum_logic
from logic import hex_editor as hexedit
from logic import inventory_tools
import subprocess, os, zipfile, requests, re, time, webbrowser, itemdata, lzma, datetime, json, savefile_io, hashlib, shutil
from os_layer import *
from pathlib import Path as PATH
#Collapse all functions to navigate. In Atom editor: "Edit > Folding > Fold All"

Toplevel = main_window.ToplevelBase
NEXUS_BUILD = os.environ.get("ER_SAVE_MANAGER_NEXUS_BUILD") == "1"


# set always the working dir to the correct folder for unix env
if not is_windows:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))


class Config:

    def __init__(self):
        if not os.path.exists(post_update_file):
            with open(post_update_file, 'w') as ff:
                ff.write("True")

        with open(post_update_file, 'r') as f:
            x = f.read()
            self.post_update = (True if x == 'True' else False)




        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                dat = json.load(f)

                if not "custom_ids" in dat.keys():  # custom_ids was an addition to v1.5, must create for current users with existing config.json from v1.5
                    dat["custom_ids"] = {}
                    self.cfg = dat

                    with open(config_path, 'w') as f:
                        json.dump(self.cfg, f)

        if not os.path.exists(config_path):  # Build dictionary for first time
            dat = {}
            dat["post_update"] = True
            dat["gamedir"] = ""
            dat["steamid"] = ""
            dat["seamless-coop"] = False
            dat["custom_ids"] = {}

            self.cfg = dat
            with open(config_path, 'w') as f:
                json.dump(self.cfg, f)
        else:
            with open(config_path, 'r') as f:
                js = json.load(f)
                self.cfg = js
    def set_update(self, val):
        self.post_update = val
        with open(post_update_file, 'w') as f:
            f.write("True" if val else "False")

    def set(self,k,v):
        self.cfg[k] = v
        with open(config_path, 'w') as f:
            json.dump(self.cfg, f)

    def add_to(self,k,v):
        self.cfg[k].update(v)
        with open(config_path, 'w') as f:
            json.dump(self.cfg, f)

    def delete_custom_id(self, k):
        self.cfg['custom_ids'].pop(k)
        with open(config_path, 'w') as f:
            json.dump(self.cfg, f)






# ///// UTILITIES /////

def popup(text, command=None, functions=False, buttons=False, button_names=("Yes", "No"), b_width=(6,6), title="Manager", parent_window=None):
    """text: Message to display on the popup window.
    command: Simply run the windows CMD command if you press yes.
    functions: Pass in external functions to be executed for yes/no"""
    def run_cmd():
        cmd_out = run_command(command)
        popupwin.destroy()
        if cmd_out[0] == "error":
            popupwin.destroy()

    def dontrun_cmd():
        popupwin.destroy()

    def run_func(arg):
        arg()
        popupwin.destroy()
    if parent_window is None:
        parent_window = root
    popupwin = Toplevel(parent_window)
    popupwin.title(title)

    lab = Label(popupwin, text=text)
    lab.grid(row=0, column=0, padx=5, pady=5, columnspan=2)
    # Places popup window at center of the root window
    x = parent_window.winfo_x()
    y = parent_window.winfo_y()
    popupwin.geometry("+%d+%d" % (x + 200, y + 200))

    # Runs for simple windows CMD execution
    if functions is False and buttons is True:
        but_yes = Button(
            popupwin, text=button_names[0], borderwidth=5, width=b_width[0], command=run_cmd
        ).grid(row=1, column=0, padx=(10, 0), pady=(0, 10))
        but_no = Button(
            popupwin, text=button_names[1], borderwidth=5, width=b_width[1], command=dontrun_cmd
        ).grid(row=1, column=1, padx=(10, 10), pady=(0, 10))

    elif functions is not False and buttons is True:
        but_yes = Button(
            popupwin,
            text=button_names[0],
            borderwidth=5,
            width=b_width[0],
            command=lambda: run_func(functions[0]),
        ).grid(row=1, column=0, padx=(10, 0), pady=(0, 10))
        but_no = Button(
            popupwin,
            text=button_names[1],
            borderwidth=5,
            width=b_width[1],
            command=lambda: run_func(functions[1]),
        ).grid(row=1, column=1, padx=(10, 10), pady=(0, 10))
    # if text is the only arguement passed in, it will simply be a popup window to display text


def archive_file(file, name, metadata, names):
    try:
        name = name.replace(" ", "_")

        if not os.path.exists(file):  # If you try to load a save from listbox, and it tries to archive the file already present in the gamedir, but it doesn't exist, then skip
            return


        now = datetime.datetime.now()
        date = now.strftime("%Y-%m-%d__(%I.%M.%S)")
        name = f"{name}__{date}"
        os.makedirs(f"./data/archive/{name}")


        with open(file, "rb") as fhi, lzma.open(f"./data/archive/{name}/ER0000.xz", 'w') as fho:
            fho.write(fhi.read())
            names = [i for i in names if not i is None]
            formatted_names = ", ".join(names)
            meta = f"{metadata}\nCHARACTERS:\n {formatted_names}"

        meta_ls = [i for i in meta]
        try:
            x = meta.encode("ascii") # Will fail with UnicodeEncodeError if special characters exist
            with open(f"./data/archive/{name}/info.txt", 'w') as f:
                f.write(meta)
        except Exception:
            for ind,i in enumerate(meta):
                try:
                    x = i.encode("ascii")
                    meta_ls[ind] = i
                except Exception:
                    meta_ls[ind] = '?'
            fixed_meta = ""
            for i in meta_ls:
                fixed_meta = fixed_meta + i

            with open(f"./data/archive/{name}/info.txt", 'w') as f:
                f.write(fixed_meta)

    except Exception as e:
        traceback.print_exc()
        str_err = "".join(traceback.format_exc())
        popup(str_err)
        return


def unarchive_file(file):
    lzc = lzma.LZMACompressor()
    name = file.split("/")[-2]
    path = f"./data/recovered/{name}/"


    if not os.path.exists("./data/recovered/"):
        os.makedirs("./data/recovered/")
    if not os.path.exists(path):
        os.makedirs(path)

    recovered_save = Path(path) / ext()
    with lzma.open(file, "rb") as f_in, open(recovered_save, "wb") as f_out:
        f_out.write(f_in.read())


def grab_metadata(file):
    """Used to grab metadata from archive info.txt"""
    with open(file.replace(" ", "__").replace(":", "."), 'r') as f:
        meta = f.read()
        popup(meta.replace(",", "\n"))


def get_charnames(file):
    """wrapper for hexedit.get_names"""



    out = hexedit.get_names(file)
    if out is False:
        popup(f"Error: Unable to get character names.\nDoes the following path exist?\n{file}")
    else:
        return out


def finish_update():
    if os.path.exists("./data/GameSaveDir.txt"):  # Legacy file for pre v1.5 versions
        os.remove("./data/GameSaveDir.txt")


    if config.post_update:  # Will be ran on first launch after running update.exe

        if not os.path.exists("./data/save-files-pre-V1.5-BACKUP"): # NONE OF THIS WILL BE RUN ON v1.5+
            try:
                copy_folder(savedir, "./data/save-files-pre-V1.5-BACKUP")
            except Exception as e:
                traceback.print_exc()
                str_err = "".join(traceback.format_exc())
                popup(str_err)

            for dir in os.listdir(savedir):  # Reconstruct save-file structure for pre v1.5 versions

                try:
                    id_matches = re.findall(r"\d{17}", str(os.listdir(f"{savedir}{dir}/")))
                    if len(id_matches) < 1:
                        continue

                    legacy_source = savefile_io.resolve_save_path(f"{savedir}{dir}/{id_matches[0]}", preferred_filename=ext())
                    shutil.move(str(legacy_source), f"{savedir}{dir}/{ext()}")
                    for i in ["GraphicsConfig.xml", "notes.txt", "steam_autocloud.vdf"]:
                        if os.path.exists(f"{savedir}{dir}/{i}"):
                            os.remove(f"{savedir}{dir}/{i}")

                    delete_folder(f"{savedir}{dir}/{id_matches[0]}")
                except Exception as e:
                    traceback.print_exc()
                    str_err = "".join(traceback.format_exc())
                    popup(str_err)
                    continue


def ext():
    return savefile_io.preferred_save_filename(config.cfg["seamless-coop"])


def resolve_save_path(directory):
    return str(savefile_io.resolve_save_path(directory, preferred_filename=ext()))


def game_save_path():
    return resolve_save_path(config.cfg["gamedir"])


def managed_save_path(slot_name):
    return resolve_save_path(f"{savedir}{slot_name.replace(' ', '-')}")


def temp_save_path(slot_index):
    return resolve_save_path(f"{temp_dir}{slot_index}")


def open_game_save_dir():
    if config.cfg["gamedir"] == "":
        popup("Please set your default game save directory first")
        return
    else:
        print(config.cfg["gamedir"])
        open_folder_standard_exporer(config.cfg["gamedir"])
        return


def open_folder():
    """Right-click open file location in listbox"""
    if len(lb.curselection()) < 1:
        popup("No listbox item selected.")
        return
    name = fetch_listbox_entry(lb)[0]
    cmd = lambda: open_folder_standard_exporer(f'{savedir}{name.replace(" ", "-")}')
    run_command(cmd)


def forcequit():
    comm = lambda: force_close_process("eldenring.exe")
    popup(text="Are you sure?", buttons=True, command=comm)


def update_app(on_start=False):
    """Gets redirect URL of latest release, then pulls the version number from URL and makes a comparison"""
    if NEXUS_BUILD:
        if not on_start:
            popup("Update checks are disabled in the Nexus Mods build. Download updates from Nexus Mods or GitHub Releases.")
        return

    try:
        version_url = "https://github.com/RorikSR/ER_Save_Manager_v2/releases/latest"
        r = requests.get(version_url)  # Get redirect url
        ver = float(r.url.split("/")[-1].split("v")[1])
    except Exception:
        popup("Can not check for updates. Check your internet connection.")
        return
    if ver > v_num:
        popup(
            text=f" Release v{str(ver)} Available\nClose the program and run the Updater.",
            buttons=True,
            functions=(root.quit, donothing),
            button_names=("Exit Now", "Cancel"),
        )

    if on_start is True:
        return
    else:
        popup("Current version up to date")
        return


def reset_default_dir():
    """DEPRECIATED! writes the original gamedir to text file"""
    global gamedir
    with open(gamesavedir_txt, "w") as fh:
        fh.write(eldenring_savedata_dir)
    with open(gamesavedir_txt, "r") as fh:
        gamedir = fh.readline()
    popup("Successfully reset default directory")


def help_me():
    # out = run_command("notepad ./data/readme.txt")
    info = ""
    with open("./data/readme.txt", "r") as f:
        dat = f.readlines()
        for line in dat:
            info = info + line
    popup(info)


def load_listbox(lstbox):
    """LOAD current save files and insert them into listbox. This is Used
    to load the listbox on startup and also after deleting an item from the listbox to refresh the entries."""
    lstbox.delete(0, END)
    count = 0
    if os.path.isdir(savedir) is True:
        for entry in sorted(os.listdir(savedir), key=str.lower):
            lstbox.insert(END, "  " + entry.replace("-", " "))
            count += 1
    if "save_count_var" in globals() and "lb" in globals() and lstbox is lb:
        save_count_var.set(f"{count} profile{'s' if count != 1 else ''} ready")


def create_save():
    """Takes user input from the create save entry box and copies files from game save dir to the save-files dir of app"""
    if len(config.cfg['gamedir']) < 2:
        popup("Set your Default Game Directory first")
        return
    name = cr_save_ent.get().strip()
    newdir = "{}{}".format(savedir, name.replace(" ", "-"))

    # Check the given name in the entry
    if len(name) < 1:
        popup("No name entered")

    isforbidden = False
    for char in name:
        if char in "~'{};:./\\,:*?<>|-!@#$%^&()+":
            isforbidden = True
    if isforbidden is True:
        popup("Forbidden character used")

    if os.path.isdir(savedir) is False:
        # subprocess.run("md .\\save-files", shell=True)
        cmd_out = run_command(lambda: os.makedirs(savedir))
        if cmd_out[0] == "error":
            return

    # If new save name doesnt exist, insert it into the listbox,
    # otherwise duplicates will appear in listbox even though the copy command will overwrite original save
    if len(name) > 0 and isforbidden is False:

        path = game_save_path()

        nms = get_charnames(path)
        if nms is False:
            nms = []
        archive_file(path, name, "ACTION: Clicked Create Save", nms)


        cp_to_saves_cmd = lambda: savefile_io.copy_save_to_directory(path, newdir, target_filename=ext())
        # /E - Copy subdirectories, including any empty ones.
        # /H - Copy files with hidden and system file attributes.
        # /C - Continue copying even if an error occurs.
        # /I - If in doubt, always assume the destination is a folder. e.g. when the destination does not exist
        # /Y - Overwrite all without PROMPT (ex: yes no)
        if os.path.isdir(newdir) is False:
            cmd_out = run_command(lambda: os.makedirs(newdir))
            if cmd_out[0] == "error":
                return
            lb.insert(END, "  " + name)
            cmd_out = run_command(cp_to_saves_cmd)
            if cmd_out[0] == "error":
                return
            create_notes(name, newdir)
            load_listbox(lb)
            cr_save_ent.delete(0, END)
            if "main_status_var" in globals():
                main_status_var.set(f"Created profile '{name}'.")
        else:
            popup(
                "File already exists, OVERWRITE?", command=cp_to_saves_cmd, buttons=True
            )
        #save_path = f"{newdir}/{user_steam_id}/ER0000.sl2"
        #nms = get_charnames(save_path)
        #archive_file(save_path, f"ACTION: Create save\nCHARACTERS: {nms}")


def donothing():
    pass


def load_save_from_lb():
    """Fetches currently selected listbox item and copies files to game save dir."""

    if len(config.cfg["gamedir"]) < 2:
        popup("Set your Default Game Directory first")
        return
    def wrapper(comm):
        """Archives savefile in gamedir and runs command to overwrite. This function is then passed into popup function."""
        #path = f"{gamedir}/{user_steam_id}/ER0000.sl2"
        path = game_save_path()
        if not os.path.exists(path):
            run_command(comm)
        else:
            nms = get_charnames(path)
            if nms is False:
                nms = []
            archive_file(path, "Loaded Save", "ACTION: Loaded save and overwrite current save file in EldenRing game directory", nms)
            run_command(comm)
        if "main_status_var" in globals():
            main_status_var.set(f"Loaded profile '{name}' into the game save directory.")

    if len(lb.curselection()) < 1:
        popup("No listbox item selected.")
        return
    name = fetch_listbox_entry(lb)[0]
    src_dir = "".join((savedir, name.replace(" ", "-"), "/"))


    comm = lambda: savefile_io.copy_save_to_directory(resolve_save_path(src_dir), config.cfg["gamedir"], target_filename=ext())
    if not os.path.isdir(f"{savedir}{name}"):
        popup(
            "Save slot does not exist.\nDid you move or delete it from data/save-files?"
        )
        lb.delete(0, END)
        load_listbox(lb)
        return
    popup("Are you sure?", buttons=True, functions=(lambda: wrapper(comm), donothing))


def run_command(subprocess_command, optional_success_out="OK"):
    """Used throughout to run commands into subprocess and capture the output. Note that
    it is integrated with popup function for in app error reporting."""
    try:
        subprocess_command()
    except Exception as e:
        traceback.print_exc()
        str_err = "".join(traceback.format_exc())
        popup(str_err)
        return ("error", str_err)
    return ("Successfully completed operation", optional_success_out)


def delete_save():
    """Removes entire directory in save-files dir"""
    name = fetch_listbox_entry(lb)[0]
    comm = lambda: delete_folder(f"{savedir}{name}")

    def yes():
        path = managed_save_path(name)
        chars = get_charnames(path)
        if chars is False:
            chars = []
        archive_file(path, name, "ACTION: Delete save file in Manager", chars)
        out = run_command(comm)
        lb.delete(0, END)
        load_listbox(lb)
        if "main_status_var" in globals():
            main_status_var.set(f"Deleted profile '{name}'.")

    def no():
        return

    popup(f"Delete {fetch_listbox_entry(lb)[1]}?", functions=(yes, no), buttons=True)


def fetch_listbox_entry(lstbox):
    """Returns currently selected listbox entry.
    internal name is for use with save directories and within this script.
    Name is used for display within the listbox"""

    name = ""
    for i in lstbox.curselection():
        name = name + lstbox.get(i)
    internal_name = name.strip().replace(" ", "-")
    return (internal_name, name)


def rename_slot():
    """Renames the name in save file listbox"""

    def cancel():
        popupwin.destroy()

    def done():
        new_name = ent.get()
        if len(new_name) < 1:
            popup("No name entered.")
            return
        isforbidden = False
        for char in new_name:
            if char in "~'{};:./\\,:*?<>|-!@#$%^&()+":
                isforbidden = True
        if isforbidden is True:
            popup("Forbidden character used")
            return
        elif isforbidden is False:
            entries = []
            for entry in os.listdir(savedir):
                entries.append(entry)
            if new_name in entries:
                popup("Name already exists")
                return

            else:
                newnm = new_name.replace(" ", "-")
                cmd = lambda: os.rename(
                    f"{savedir}{lst_box_choice}", f"{savedir}{newnm}"
                )
                run_command(cmd)
                lb.delete(0, END)
                load_listbox(lb)
                popupwin.destroy()

    lst_box_choice = fetch_listbox_entry(lb)[0]
    if len(lst_box_choice) < 1:
        popup("No listbox item selected.")
        return

    popupwin = Toplevel(root)
    popupwin.title("Rename")
    # popupwin.geometry("200x70")
    lab = Label(popupwin, text="Enter new Name:")
    lab.grid(row=0, column=0)
    ent = Entry(popupwin, borderwidth=5)
    ent.grid(row=1, column=0, padx=25, pady=10)
    x = root.winfo_x()
    y = root.winfo_y()
    popupwin.geometry("+%d+%d" % (x + 200, y + 200))
    but_done = Button(popupwin, text="Done", borderwidth=5, width=6, command=done)
    but_done.grid(row=2, column=0, padx=(25, 65), pady=(0, 15), sticky="w")
    but_cancel = Button(popupwin, text="Cancel", borderwidth=5, width=6, command=cancel)
    but_cancel.grid(row=2, column=0, padx=(70, 0), pady=(0, 15))


def update_slot():
    """Update the selected savefile with the current elden ring savedata"""
    def do(file):
        names = get_charnames(file)
        if names is False:
            names = []
        archive_file(file, lst_box_choice, "ACTION: Clicked Update save-file in Manager", names)
        savefile_io.copy_save_to_directory(game_save_path(), f"{savedir}{lst_box_choice}", target_filename=ext())


    lst_box_choice = fetch_listbox_entry(lb)[0]
    if len(lst_box_choice) < 1:
        popup("No listbox item selected.")
        return
    path = managed_save_path(lst_box_choice)

    popup(text="This will take your current save in-game\nand overwrite this save slot\nAre you sure?", buttons=True, command=lambda: do(path))


def change_default_dir():
    """Opens file explorer for user to choose new default elden ring directory. Writes changes to GameSaveDir.txt"""

    newdir = fd.askdirectory()
    if len(newdir) < 1:  # User presses cancel
        return

    folder = newdir.split("/")[-1]
    f_id_matches = re.findall(r"\d{17}", folder)

    if len(f_id_matches) == 0:
        popup("Please select the directory named after your 17 digit SteamID")
        return


    else:

        config.set("gamedir", newdir)

        popup(f"Directory set to:\n {newdir}\n")


def rename_char(file, nw_nm, dest_slot):
    """Wrapper for hexedit.change_name for error handling"""
    try:
        x = hexedit.change_name(file, nw_nm, dest_slot)
        if x == "error":
            raise Exception
    except Exception:
        popup("Error renaming character. This may happen\nwith short names like '4'.")
        raise


def changelog(run=False):
    info = ""
    with open("./data/changelog.txt", "r") as f:
        dat = f.readlines()
        for line in dat:
            info = info + f"\n\u2022 {line}\n"
    if run:
        popup(info, title="Changelog")
        return
    if config.post_update:
        popup(info, title="Changelog")









# ////// MENUS //////

def char_manager_menu():
    """Entire character manager window for copying characters between save files"""

    def readme():
        info = ""
        with open("./data/copy-readme.txt", "r") as f:
            dat = f.readlines()
            for line in dat:
                info = info + line
        popup(info)
        # run_command("notepad ./data/copy-readme.txt")

    def open_video():
        webbrowser.open_new_tab(video_url)

    def get_char_names(lstbox, drop, v):
        """Populates dropdown menu containing the name of characters in a save file"""
        v.set("Character")
        name = fetch_listbox_entry(lstbox)[0]
        if len(name) < 1:
            return
        file = managed_save_path(name)
        names = get_charnames(file)



        drop["menu"].delete(0, "end")  # remove full list

        index = 1
        for ind, opt in enumerate(names):
            if not opt is None:
                opt = f"{index}. {opt}"
                drop["menu"].add_command(label=opt, command=TKIN._setit(v, opt))
                index += 1
            elif opt is None:
                opt = f"{ind + 1}. "
                drop["menu"].add_command(label=opt, command=TKIN._setit(v, opt))
                index += 1

    def do_copy():
        def pop_up(txt, bold=True):
            """Basic popup window used only for parent function"""
            win = Toplevel(popupwin)
            win.title("Manager")
            lab = Label(win, text=txt)
            if bold is True:
                lab.config(font=bolded)
            lab.grid(row=0, column=0, padx=15, pady=15, columnspan=2)
            x = popupwin.winfo_x()
            y = popupwin.winfo_y()
            win.geometry("+%d+%d" % (x + 200, y + 200))

        src_char = vars1.get()  # "1. charname"
        dest_char = vars2.get()
        if src_char == "Character" or dest_char == "Character":
            pop_up("Select a character first")
            return

        if src_char.split(".")[1] == " " or dest_char.split(".")[1] == " ":
            pop_up(
                "Can't write to empty slot.\nGo in-game and create a character to overwrite."
            )
            return

        name1 = fetch_listbox_entry(lb1)[0]  # Save file name. EX: main
        name2 = fetch_listbox_entry(lb2)[0]

        if len(name1) < 1 or len(name2) < 1:
            pop_up(txt="Slot not selected")
            return
        if src_char == "Character" or dest_char == "Character":
            pop_up(txt="Character not selected")
            return

        src_file = managed_save_path(name1)
        dest_file = managed_save_path(name2)

        src_ind = int(src_char.split(".")[0])
        dest_ind = int(dest_char.split(".")[0])

        # Duplicate names check
        src_char_real = src_char.split(". ")[1]
        dest_names = get_charnames(dest_file)
        nms = [i for i in dest_names]  # For archive_file only
        src_names = get_charnames(src_file)

        # If there are two or more of the name name in a destination file, quits
        rmv_none = [i for i in dest_names if not i is None]
        if max(Counter(rmv_none).values()) > 1:
            pop_up(
                """Sorry, Can't handle writing to a DESTINATION file with duplicate character names!\n\n
                You can work around this limitation by using the save file with duplicate character names as the SOURCE file:\n
                1. Select the save file with duplicate character names as the SOURCE file.\n
                2. Select a different save file as the DESTINATION (can be anything).\n
                3. Copy the first character with duplicate names to DESTINATION file\n
                4. Rename the character in the DESTINATION file to something different.\n
                5. Copy the second character with duplicate names to the DESTINATION file.\n\n
                Why do you have to do this? Because character names vary greatly in frequency and location\n
                within the save file, so this tool must replace ALL occurences of a given name.""",
                bold=False,
            )
            return

        src_names.pop(src_ind - 1)
        dest_names.pop(dest_ind - 1)
        backup_path = str(Path(temp_dir) / ext())

        # If performing operations on the same file. Changes name to random, copies character to specified slot, then rewrites the name and re-populates the dropdown entries
        if src_file == dest_file:
            archive_file(dest_file, name2, "ACTION: Copy Character", nms)
            cmd = lambda: copy_file(src_file, backup_path)
            x = run_command(cmd)
            rand_name = hexedit.random_str()
            rename_char(backup_path, rand_name, src_ind)  # Change backup to random name
            hexedit.copy_save(backup_path, src_file, src_ind, dest_ind)
            rename_char(src_file, rand_name, dest_ind)
            get_char_names(lb1, dropdown1, vars1)
            get_char_names(lb2, dropdown2, vars2)
            vars1.set("Character")
            vars2.set("Character")
            pop_up(
                txt="Success!\nDuplicate names not supported\nGenerated a new random name",
                bold=False,
            )
            return

        # If source name in destination file, copies source file to temp folder, changes the name of copied save to random, then copies source character of
        #  copied file to destination save file, and rewrites names on destination file
        elif src_char_real in dest_names:
            archive_file(dest_file, name2, "ACTION: Copy character", nms)
            cmd = lambda: copy_file(src_file, backup_path)
            x = run_command(cmd)
            rand_name = hexedit.random_str()
            rename_char(backup_path, rand_name, src_ind)

            hexedit.copy_save(backup_path, dest_file, src_ind, dest_ind)
            rename_char(dest_file, rand_name, dest_ind)

            get_char_names(lb1, dropdown1, vars1)
            get_char_names(lb2, dropdown2, vars2)
            vars1.set("Character")
            vars2.set("Character")
            pop_up(
                txt="Duplicate names not supported\nGenerated a new random name",
                bold=False,
            )
            return

        archive_file(dest_file, name2, f"ACTION: Copy character", nms)
        hexedit.copy_save(src_file, dest_file, src_ind, dest_ind)
        rename_char(dest_file, src_char_real, dest_ind)

        get_char_names(lb1, dropdown1, vars1)
        get_char_names(lb2, dropdown2, vars2)

        vars1.set("Character")
        vars2.set("Character")

        pop_up(txt="Success!")

    def cancel():
        popupwin.destroy()

    # Main GUI content
    popupwin = Toplevel(root)
    popupwin.title("Character Manager")
    popupwin.resizable(width=True, height=True)
    popupwin.geometry("620x500")

    bolded = FNT.Font(weight="bold")  # will use the default font

    x = root.winfo_x()
    y = root.winfo_y()
    popupwin.geometry("+%d+%d" % (x + 200, y + 200))

    menubar = Menu(popupwin)
    popupwin.config(
        menu=menubar
    )  # menu is a parameter that lets you set a menubar for any given window

    helpmen = Menu(menubar, tearoff=0)
    helpmen.add_command(label="Readme", command=readme)
    helpmen.add_command(label="Watch Video", command=open_video)
    menubar.add_cascade(label="Help", menu=helpmen)

    srclab = Label(popupwin, text="Source File")
    srclab.config(font=bolded)
    srclab.grid(row=0, column=0, padx=(70, 0), pady=(20, 0))

    lb1 = Listbox(popupwin, borderwidth=3, width=15, height=10, exportselection=0)
    lb1.config(font=bolded)
    lb1.grid(row=1, column=0, padx=(70, 0), pady=(0, 0))
    load_listbox(lb1)

    destlab = Label(popupwin, text="Destination File")
    destlab.config(font=bolded)
    destlab.grid(row=0, column=1, padx=(175, 0), pady=(20, 0))

    lb2 = Listbox(popupwin, borderwidth=3, width=15, height=10, exportselection=0)
    lb2.config(font=bolded)
    lb2.grid(row=1, column=1, padx=(175, 0), pady=(0, 0))
    load_listbox(lb2)

    opts = [""]
    opts2 = [""]
    vars1 = StringVar(popupwin)
    vars1.set("Character")

    vars2 = StringVar(popupwin)
    vars2.set("Character")

    dropdown1 = OptionMenu(popupwin, vars1, *opts)
    dropdown1.grid(row=4, column=0, padx=(70, 0), pady=(20, 0))

    dropdown2 = OptionMenu(popupwin, vars2, *opts2)
    dropdown2.grid(row=4, column=1, padx=(175, 0), pady=(20, 0))

    but_select1 = Button(
        popupwin, text="Select", command=lambda: get_char_names(lb1, dropdown1, vars1)
    )
    but_select1.grid(row=3, column=0, padx=(70, 0), pady=(10, 0))

    but_select2 = Button(
        popupwin, text="Select", command=lambda: get_char_names(lb2, dropdown2, vars2)
    )
    but_select2.grid(row=3, column=1, padx=(175, 0), pady=(10, 0))

    but_copy = Button(popupwin, text="Copy", command=do_copy)
    but_copy.config(font=bolded)
    but_copy.grid(row=5, column=1, padx=(175, 0), pady=(50, 0))

    but_cancel = Button(popupwin, text="Cancel", command=cancel)
    but_cancel.config(font=bolded)
    but_cancel.grid(row=5, column=0, padx=(70, 0), pady=(50, 0))

    #mainloop()


def rename_characters_menu():
    """Opens popup window and renames character of selected listbox item"""

    def do():
        choice = char_vars.get()
        choice_real = choice.split(". ")[1]
        slot_ind = int(choice.split(".")[0])
        new_name = name_ent.get()
        if len(new_name) > 16:
            popup("Name too long. Maximum of 16 characters")
            return
        if len(new_name) < 1:
            popup("Enter a name first")
            return
        if len(new_name) < 3:
            popup("Minimum 3 characters")
            return

        # Duplicate names check
        dest_names = [i for i in names]
        dest_names.pop(slot_ind - 1)

        if new_name in dest_names:
            popup("Save can not have duplicate names")
            return

        archive_file(path, choice_real, "ACTION: Rename Character", names)
        rename_char(path, new_name, slot_ind)
        popup("Successfully Renamed Character")
        drop["menu"].delete(0, "end")
        rwin.destroy()

    name = fetch_listbox_entry(lb)[0]
    if name == "":
        popup("No listbox item selected.")
        return
    path = managed_save_path(name)
    names = get_charnames(path)
    if names is False:
        popup("FileNotFoundError: This is a known issue.\nPlease try re-importing your save file.")


    chars = []
    for ind, i in enumerate(names):
        if i != None:
            chars.append(f"{ind +1}. {i}")

    rwin = Toplevel(root)
    rwin.title("Rename Character")
    rwin.resizable(width=True, height=True)
    rwin.geometry("300x200")

    bolded = FNT.Font(weight="bold")  # will use the default font
    x = root.winfo_x()
    y = root.winfo_y()
    rwin.geometry("+%d+%d" % (x + 200, y + 200))

    opts = chars
    char_vars = StringVar(rwin)
    char_vars.set("Character")

    info_lab = Label(rwin, text="Note: If you have more than one character\nwith the same name,\nthis will rename BOTH characters.\n\n")
    info_lab.pack()

    drop = OptionMenu(rwin, char_vars, *opts)
    drop.pack()
#    drop.grid(row=0, column=0, padx=(35, 0), pady=(10, 0))

    name_ent = Entry(rwin, borderwidth=5)
    name_ent.pack()
#    name_ent.grid(row=1, column=0, padx=(35, 0), pady=(10, 0))

    but_go = Button(rwin, text="Rename", borderwidth=5, command=do)
    but_go.pack()



def stat_editor_menu():
    def recalc_lvl():
        # entries = [vig_ent, mind_ent, end_ent, str_ent, dex_ent, int_ent, fai_ent, arc_ent]
        lvl = 0
        try:
            for ent in entries:
                lvl += int(ent.get())
            lvl_var.set(f"Level: {lvl - 79}")
        except Exception as e:
            return

    def set_stats():
        stats = []
        try:
            for ent in entries:
                stats.append(int(ent.get()))
        except Exception as e:
            pop_up(f"Error: Make sure all fields are completed.\n{e}")
            return
        if sum(stats) - 79 < 5:
            pop_up("Character level too low.")
            return

        vig = stats[0]
        mind_stat = stats[1]
        end = stats[2]

        char = char_vars.get().split(". ")[1]
        char_slot = int(char_vars.get().split(".")[0])
        name = fetch_listbox_entry(lb1)[0]
        file = managed_save_path(name)
        try:
            nms = get_charnames(file)
            archive_file(file, name, "ACTION: Edit stats", nms)
            hexedit.set_stats(file, char_slot, stats)
            hexedit.set_attributes(file, char_slot, [vig, mind_stat, end])
            pop_up("Success!")
        except Exception as e:
            pop_up("Something went wrong!: ", e)
            return

    def pop_up(txt, bold=True):
        """Basic popup window used only for parent function"""
        win = Toplevel(popupwin)
        win.title("Manager")
        lab = Label(win, text=txt)
        if bold is True:
            lab.config(font=bolded)
        lab.grid(row=0, column=0, padx=15, pady=15, columnspan=2)
        x = popupwin.winfo_x()
        y = popupwin.winfo_y()
        win.geometry("+%d+%d" % (x + 200, y + 200))

    def validate(P):
        if len(P) == 0:
            return True
        elif len(P) < 3 and P.isdigit() and int(P) > 0:
            return True
        else:
            # Anything else, reject it
            return False

    def get_char_names(lstbox, drop, v):
        """Populates dropdown menu containing the name of characters in a save file"""
        v.set("Character")
        name = fetch_listbox_entry(lstbox)[0]
        if len(name) < 1:
            return
        file = managed_save_path(name)
        names = get_charnames(file)

        if names is False:
            popup("FileNotFoundError: This is a known issue.\nPlease try re-importing your save file.")

        drop["menu"].delete(0, "end")  # remove full list

        index = 1
        for ind, opt in enumerate(names):
            if not opt is None:
                opt = f"{index}. {opt}"
                drop["menu"].add_command(label=opt, command=TKIN._setit(v, opt))
                index += 1
            elif opt is None:
                opt = f"{ind + 1}. "
                drop["menu"].add_command(label=opt, command=TKIN._setit(v, opt))
                index += 1

    def get_char_stats():
        char = char_vars.get()

        if char == "Character":
            pop_up("Select a Character first")
            return

        char = char_vars.get().split(". ")[1]
        char_slot = int(char_vars.get().split(".")[0])
        name = fetch_listbox_entry(lb1)[0]
        file = managed_save_path(name)

        try:
            stats = hexedit.get_stats(file, char_slot)[0]
        except Exception as e:
            #pop_up("Can't get stats, go in-game and\nload into the character first or try leveling up once.")
            popup("Unable to aquire stats/level.\nYour character level may be incorrect.\nFix now?",functions=(lambda:fix_stats_menu(file, char_slot), lambda:popupwin.destroy()), buttons=True, button_names=("Yes", "No"), parent_window=popupwin)
            return

        # entries = [vig_ent, mind_ent, end_ent, str_ent, dex_ent, int_ent, fai_ent, arc_ent]
        if 0 in stats:
            pop_up("Can't get stats, go in-game and\nload into the character first or try leveling up once.")
            return

        for stat, entry in list(zip(stats, entries)):
            entry.delete(0, END)
            entry.insert(1, stat)
        lvl = sum(stats) - 79
        lvl_var.set(f"Level: {lvl}")

    # Main GUI content STAT
    popupwin = Toplevel(root)
    popupwin.title("Stat Editor")
    popupwin.resizable(width=True, height=True)
    popupwin.geometry("580x550")
    vcmd = (popupwin.register(validate), "%P")
    bolded = FNT.Font(weight="bold")  # will use the default font
    x = root.winfo_x()
    y = root.winfo_y()
    popupwin.geometry("+%d+%d" % (x + 200, y + 200))

    menubar = Menu(popupwin)
    popupwin.config(menu=menubar)
    helpmenu = Menu(menubar, tearoff=0)
    #helpmenu.add_command(label="Important Info", command=lambda: pop_up("\u2022 Offline use only! Using this feature may get you banned."))
    #helpmenu.add_command(label="Watch Video", command=lambda: webbrowser.open_new_tab(stat_edit_video))
    menubar.add_cascade(label="MAY BE UNSAFE ONLINE!", menu=helpmenu)

    # MAIN SAVE FILE LISTBOX
    lb1 = Listbox(popupwin, borderwidth=3, width=15, height=10, exportselection=0)
    lb1.config(font=bolded)
    lb1.grid(row=0, column=0, padx=(55, 0), pady=(35, 295), sticky="n")
    load_listbox(lb1)

    # SELECT LISTBOX ITEM BUTTON
    but_select1 = Button(
        popupwin, text="Select", command=lambda: get_char_names(lb1, dropdown1, char_vars)
    )
    but_select1.grid(row=0, column=0, padx=(55, 0), pady=(50, 0))

    # DROPDOWN MENU STUFF
    opts = [""]
    char_vars = StringVar(popupwin)
    char_vars.set("Character")
    dropdown1 = OptionMenu(popupwin, char_vars, *opts)
    dropdown1.grid(row=0, column=0, padx=(55, 0), pady=(120, 0))

    # GET STATS BUTTON
    but_getstats = Button(popupwin, text="Get Stats", command=get_char_stats)
    but_getstats.grid(row=0, column=0, padx=(55, 0), pady=(210, 0))

    # VIGOR
    vig_lab = Label(popupwin, text="VIGOR:")
    vig_lab.config(font=bolded)
    vig_lab.grid(row=0, column=1, padx=(60, 0), pady=(35, 0), sticky="n")

    vig_ent = Entry(
        popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd
    )
    vig_ent.grid(row=0, column=1, padx=(160, 0), pady=(35, 0), sticky="n")

    # MIND
    mind_lab = Label(popupwin, text="MIND:")
    mind_lab.config(font=bolded)
    mind_lab.grid(row=0, column=1, padx=(60, 0), pady=(75, 0), sticky="n")

    mind_ent = Entry(
        popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd
    )
    mind_ent.grid(row=0, column=1, padx=(160, 0), pady=(75, 0), sticky="n")

    # ENDURANCE
    end_lab = Label(popupwin, text="END:")
    end_lab.config(font=bolded)
    end_lab.grid(row=0, column=1, padx=(60, 0), pady=(115, 0), sticky="n")

    end_ent = Entry(
        popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd
    )
    end_ent.grid(row=0, column=1, padx=(160, 0), pady=(115, 0), sticky="n")

    # STRENGTH
    str_lab = Label(popupwin, text="STR:")
    str_lab.config(font=bolded)
    str_lab.grid(row=0, column=1, padx=(60, 0), pady=(155, 0), sticky="n")

    str_ent = Entry(
        popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd
    )
    str_ent.grid(row=0, column=1, padx=(160, 0), pady=(155, 0), sticky="n")

    # DEXTERITY
    dex_lab = Label(popupwin, text="DEX:")
    dex_lab.config(font=bolded)
    dex_lab.grid(row=0, column=1, padx=(60, 0), pady=(195, 0), sticky="n")

    dex_ent = Entry(
        popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd
    )
    dex_ent.grid(row=0, column=1, padx=(160, 0), pady=(195, 0), sticky="n")

    # INTELLIGENCE
    int_lab = Label(popupwin, text="INT:")
    int_lab.config(font=bolded)
    int_lab.grid(row=0, column=1, padx=(60, 0), pady=(235, 0), sticky="n")

    int_ent = Entry(
        popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd
    )
    int_ent.grid(row=0, column=1, padx=(160, 0), pady=(235, 0), sticky="n")

    # FAITH
    fai_lab = Label(popupwin, text="FAITH:")
    fai_lab.config(font=bolded)
    fai_lab.grid(row=0, column=1, padx=(60, 0), pady=(275, 0), sticky="n")

    fai_ent = Entry(
        popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd
    )
    fai_ent.grid(row=0, column=1, padx=(160, 0), pady=(275, 0), sticky="n")

    # ARCANE
    arc_lab = Label(popupwin, text="ARC:")
    arc_lab.config(font=bolded)
    arc_lab.grid(row=0, column=1, padx=(60, 0), pady=(315, 0), sticky="n")

    arc_ent = Entry(
        popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd
    )
    arc_ent.grid(row=0, column=1, padx=(160, 0), pady=(315, 0), sticky="n")

    # lIST OF ALL ENTRIES
    entries = [vig_ent, mind_ent, end_ent, str_ent, dex_ent, int_ent, fai_ent, arc_ent]

    # BOX THAT SHOWS CHAR LEVEL
    lvl_var = StringVar()
    lvl_var.set("Level: ")
    lvl_box = Entry(
        popupwin, borderwidth=2, width=10, textvariable=lvl_var, state=DISABLED
    )
    lvl_box.config(font=bolded)
    lvl_box.grid(row=0, column=1, padx=(70, 0), pady=(355, 0), sticky="n")

    # RECALCULATE LVL BUTTON
    but_recalc_lvl = Button(popupwin, text="Recalc", command=recalc_lvl)
    but_recalc_lvl.grid(row=0, column=1, padx=(220, 0), pady=(355, 0), sticky="n")

    # SET STATS BUTTON
    but_set_stats = Button(popupwin, text="Set Stats", command=set_stats)
    but_set_stats.config(font=bolded)
    but_set_stats.grid(row=0, column=1, padx=(0, 135), pady=(450, 0), sticky="n")


def set_steam_id_menu():

    def done():
        file = managed_save_path(name)
        steam_id_val = ent.get()
        x = re.findall(r"\d{17}", str(steam_id_val))
        if len(x) < 1:
            popup("Your id should be a 17 digit number.")
            return
        nms = get_charnames(file)
        archive_file(file, name, "ACTION: Changed SteamID", nms)
        out = hexedit.replace_id(file, int(x[0]))
        if out is False:
            popup("Unable to find SteamID, SaveData may be corrupt.")
            return
        popup("Successfully changed SteamID")
        popupwin.destroy()

    def cancel():
        popupwin.destroy()

    def validate(P):
        if len(P) == 0:
            return True
        elif len(P) < 18 and P.isdigit():
            return True
        else:
            # Anything else, reject it
            return False

    name = fetch_listbox_entry(lb)[0]
    if name == "":
        popup("No listbox item selected.")
        return
    cur_id = hexedit.get_id(managed_save_path(name))

    popupwin = Toplevel(root)
    popupwin.title("Set SteamID")
    vcmd = (popupwin.register(validate), "%P")
    # popupwin.geometry("200x70")
    id_lab = Label(popupwin, text=f"Current ID: {cur_id}")
    id_lab.grid(row=0, column=0)
    lab = Label(popupwin, text="Enter new ID:")
    lab.grid(row=1, column=0)

    ent = Entry(popupwin, borderwidth=5, validate="key", validatecommand=vcmd)
    ent.grid(row=2, column=0, padx=25, pady=10)
    x = root.winfo_x()
    y = root.winfo_y()
    popupwin.geometry("+%d+%d" % (x + 200, y + 200))
    but_done = Button(popupwin, text="Done", borderwidth=5, width=6, command=done)
    but_done.grid(row=3, column=0, padx=(25, 65), pady=(0, 15), sticky="w")
    but_cancel = Button(popupwin, text="Cancel", borderwidth=5, width=6, command=cancel)
    but_cancel.grid(row=3, column=0, padx=(70, 0), pady=(0, 15))


def inventory_editor_menu():
    item_options = []

    def pop_up(txt, bold=True):
        """Basic popup window used only for parent function"""
        win = Toplevel(popupwin)
        win.title("Manager")
        lab = Label(win, text=txt)
        if bold is True:
            lab.config(font=bolded)
        lab.grid(row=0, column=0, padx=15, pady=15, columnspan=2)
        x = popupwin.winfo_x()
        y = popupwin.winfo_y()
        win.geometry("+%d+%d" % (x + 200, y + 200))


    def get_char_names(lstbox, drop, v):
        """Populates dropdown menu containing the name of characters in a save file"""
        v.set("Character")
        name = fetch_listbox_entry(lstbox)[0]
        if len(name) < 1:
            return
        file = managed_save_path(name)
        names = get_charnames(file)
        if names is False:
            popup("FileNotFoundError: This is a known issue.\nPlease try re-importing your save file.")
        drop["menu"].delete(0, "end")  # remove full list

        index = 1
        for ind, opt in enumerate(names):
            if not opt is None:
                opt = f"{index}. {opt}"
                drop["menu"].add_command(label=opt, command=TKIN._setit(v, opt))
                index += 1
            elif opt is None:
                opt = f"{ind + 1}. "
                drop["menu"].add_command(label=opt, command=TKIN._setit(v, opt))
                index += 1


    def validate(P):
        if len(P) == 0:
            return True
        elif len(P) < 4 and P.isdigit() and int(P) > 0:
            return True
        else:
            # Anything else, reject it
            return False


    def add():
        char = c_vars.get()  # "1. charname"
        if char == "Character" or char == "":
            pop_up("Character not selected")
            return

        item = i_vars.get()
        if item == "Items" or item == "":
            pop_up("Select an item first.")
            return

        if char.split(".")[1] == " ":
            pop_up(
                "Can't write to empty slot.\nGo in-game and create a character to overwrite."
            )
            return

        name = fetch_listbox_entry(lb1)[0]  # Save file name. EX: main
        if len(name) < 1:
            pop_up(txt="Slot not selected")
            return

        dest_file = managed_save_path(name)
        char_ind = int(char.split(".")[0])

        qty = qty_ent.get()
        if qty == "":
            pop_up("Set a quantity first.")
            return
        else:
            qty = int(qty)
        itemid = itemdb.db[cat_vars.get()].get(item)
        archive_file(dest_file, name, "ACTION: Add inventory items", get_charnames(dest_file))
        x = hexedit.additem(dest_file, char_ind, itemid, qty)
        # x = hexedit.additem(dest_file,char_ind,item, qty)
        if x is None:
            pop_up(
                "Unable to set quantity. Ensure you have at least 1 of the selected items.\nIf you already have one of the items in your inventory and are still unable to set the quantity,\nGo to Custom Items > Search and manually scan for the item ID."
            )
        else:
            pop_up("Successfully added items")
        return


    def populate_items(*args):
        nonlocal item_options
        global itemdb
        """Populates the item dropdown by getting category"""

        cat = cat_vars.get()
        itemdb = itemdata.Items()
        item_options = itemdb.get_item_ls(cat)
        refresh_items()

    def refresh_items(*args):
        query = item_search_var.get().strip().lower()
        items = [
            item
            for item in item_options
            if len(item) > 1 and (not query or query in item.lower())
        ]
        dropdown3["menu"].delete(0, "end")  # remove full list
        for i in items:
            dropdown3["menu"].add_command(label=i, command=TKIN._setit(i_vars, i))

        if i_vars.get() not in items:
            i_vars.set("Items")  # default value set


    def manual_search():
        try:
            delete_folder(f"{temp_dir}1")
            delete_folder(f"{temp_dir}2")
            delete_folder(f"{temp_dir}3")
        except Exception as e:
            pass
        popupwin.destroy()
        find_itemid()


    def add_custom_id():
        def done():
            name = name_ent.get()
            ids = [id_ent1.get(), id_ent2.get()]
            if len(ids[0]) < 1 or len(ids[1]) < 1:
                return
            custom_id_val = [ int(ids[0]), int(ids[1]) ]
            try:
                config.add_to("custom_ids", {name:custom_id_val})
            except Exception as e:
                popup(f"Error:\n\n{repr(e)}")
                return

            idwin.destroy()
            popupwin.destroy()
            inventory_editor_menu()


        def validate_id(P):
            if len(P) > 0 and len(P) < 4 and P.isdigit():
                return True
            else:
                return False

        def validate_name(P):
            if len(P) > 0 and len(P) < 29 and P.isdigit() is False:
                return True
            else:
                return False
        idwin = Toplevel(root)
        idwin.title("Add Custom ID")
        vcmd_id = (idwin.register(validate_id), "%P")
        vcmd_name = (idwin.register(validate_name), "%P")
        # popupwin.geometry("200x70")

        x = root.winfo_x()
        y = root.winfo_y()
        idwin.geometry("+%d+%d" % (x + 200, y + 200))

        name_lab = Label(idwin, text="Item Name: ")
        name_lab.grid(row=0, column=0, padx=(0,0), pady=(10,0))
        name_ent = Entry(idwin, borderwidth=5, width=25, validate="key", validatecommand=vcmd_name)
        name_ent.grid(row=1, column=0, padx=(20,20), pady=(10,0))


        id_lab = Label(idwin, text="ID: ")
        id_lab.grid(row=2, column=0, padx=(20,0), pady=(15,15), sticky='w')

        id_ent1 = Entry(idwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd_id)
        id_ent1.grid(row=2, column=0, padx=(50,0), pady=(15,15), sticky='w')

        id_ent2 = Entry(idwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd_id)
        id_ent2.grid(row=2, column=0,  padx=(80,0), pady=(15,15), sticky='w')


        but_done = Button(idwin, text="Add", borderwidth=5, width=6, command=done)
        but_done.grid(row=2, column=0, sticky='w', padx=(120,0), pady=(15,15))


    def find_itemid():

        def validate(P):
            if len(P) == 0:
                return True
            elif len(P) < 4 and P.isdigit() and int(P) > 0:
                return True
            else:
                return False


        def load_temp_save(pos):
            if config.cfg["gamedir"] == "" or len(config.cfg["gamedir"]) < 2:
                popup("Please set your Default Game Directory first")
                return
            if os.path.isdir(temp_dir) is False:
                cmd_out = run_command(lambda: os.makedirs(temp_dir))
                if cmd_out[0] == "error":
                    popup("Error! unable to make temp directory.")
                    return

            if os.path.isdir(f"{temp_dir}1") is False:
                cmd_out = run_command(lambda: os.makedirs(f"{temp_dir}1"))
                if cmd_out[0] == "error":
                    popup("Error! unable to make temp directory.")
                    return

            if os.path.isdir(f"{temp_dir}2") is False:
                cmd_out = run_command(lambda: os.makedirs(f"{temp_dir}2"))
                if cmd_out[0] == "error":
                    popup("Error! unable to make temp directory.")
                    return

            if os.path.isdir(f"{temp_dir}3") is False:
                cmd_out = run_command(lambda: os.makedirs(f"{temp_dir}3"))
                if cmd_out[0] == "error":
                    popup("Error! unable to make temp directory.")
                    return


            if pos == 1:
                copied_path = savefile_io.copy_save_to_directory(game_save_path(), f"{temp_dir}/1", target_filename=ext())
                file_paths[0] = str(copied_path)


            if pos == 2:
                copied_path = savefile_io.copy_save_to_directory(game_save_path(), f"{temp_dir}/2", target_filename=ext())
                file_paths[1] = str(copied_path)

            if pos == 3:
                copied_path = savefile_io.copy_save_to_directory(game_save_path(), f"{temp_dir}/3", target_filename=ext())
                file_paths[2] = str(copied_path)

            window.lift()

        def name_id_popup(id):
            def add_custom_id(id):
                name = name_ent.get()
                if len(name) > 16:
                    popup("Name too long", parent_window=window)
                    return

                try:

                    config.add_to("custom_ids", {name:id})
                    window.destroy()
                    inventory_editor_menu()


                except Exception as e:
                    popup(f"Something went wrong.\nvalues: {name, id}\nError: {e}")
                    return
                popupwin.destroy()

            popupwin = Toplevel(window)
            popupwin.title("Add Item ID")
            vcmd = (popupwin.register(validate), "%P")
            # popupwin.geometry("200x70")

            lab = Label(popupwin, text=f"Item ID: {id}\nEnter item name:")
            lab.grid(row=0, column=0)
            name_ent = Entry(popupwin, borderwidth=5)
            name_ent.grid(row=1, column=0, padx=25, pady=10)
            x = window.winfo_x()
            y = window.winfo_y()
            popupwin.geometry("+%d+%d" % (x + 200, y + 200))
            but_done = Button(popupwin, text="Add", borderwidth=5, width=6, command=lambda: add_custom_id(id))
            but_done.grid(row=2, column=0, padx=(25, 65), pady=(0, 15), sticky="w")
            but_cancel = Button(popupwin, text="Cancel", borderwidth=5, width=6, command=lambda: popupwin.destroy())
            but_cancel.grid(row=2, column=0, padx=(70, 0), pady=(0, 15))


        def multi_item_select(indexes):
            def grab_id(listbox):
                ind = fetch_listbox_entry(listbox)[0].split(":")[0]

                if ind == '':
                    popup("No value selected!")
                    return
                else:
                    popupwin.destroy()
                    name_id_popup(indexes[int(ind)])

            popupwin = Toplevel(window)
            popupwin.title("Add Item ID")
            vcmd = (popupwin.register(validate), "%P")
            x = window.winfo_x()
            y = window.winfo_y()
            popupwin.geometry("+%d+%d" % (x + 200, y + 200))
            lab = Label(popupwin, text=f"Multiple locations found! Select an address.\nLower addresses have a higher chance of success.")
            lab.grid(row=0, column=0, padx=(5,5))

            lb1 = Listbox(popupwin, borderwidth=3, width=19, height=10, exportselection=0)
            lb1.config(font=bolded)
            lb1.grid(row=1, column=0)

            but_select = Button(popupwin, text="Select", borderwidth=5, width=6, command=lambda:grab_id(lb1))
            but_select.grid(row=2, column=0, padx=(50, 65), pady=(5, 15), sticky="w")
            but_cancel = Button(popupwin, text="Cancel", borderwidth=5, width=6, command=lambda: popupwin.destroy())
            but_cancel.grid(row=2, column=0, padx=(85, 0), pady=(5, 15))
            # Insert itemids alongside addresses so users can see if ids are like [0,0] and thus wrong
            for k,v in indexes.items():
                if v == [0, 0]: # Obviously not an item ID
                    continue
                lb1.insert(END, "  " + f"{k}: {v}")



        def search():

            valid = True
            # VALIDATE USER INPUTS

            if len([i for i in file_paths if not i == 0]) < 3:
                popup("Not all save files selected.", parent_window=window)
                return

            if len(q1_ent.get())< 1 or len(q2_ent.get()) < 1 or len(q3_ent.get()) < 1:
                popup("Enter a quantity for all save files.", parent_window=window)
                return

            for p in file_paths:
                if not os.path.exists(p):
                    valid = False
            if not valid:
                popup("Invalid paths")
                return


            item_id = hexedit.search_itemid(file_paths[0], file_paths[1], file_paths[2], q1_ent.get(), q2_ent.get(), q3_ent.get())
            if item_id is None:
                popup("Unable to find item ID")
                return
            if item_id[0] == "match":
                name_id_popup(item_id[1])

            if item_id[0] == "multi-match":
                multi_item_select(item_id[1])

            delete_folder(f"{temp_dir}1")
            delete_folder(f"{temp_dir}2")
            delete_folder(f"{temp_dir}3")
        def callback(url):
            webbrowser.open_new(url)




        file_paths = [0,0,0]

        window = Toplevel(root)
        window.title("Inventory Editor")
        window.resizable(width=True, height=True)
        window.geometry("530x560")

        vcmd = (window.register(validate), "%P")

        bolded = FNT.Font(weight="bold")  # will use the default font

        x = root.winfo_x()
        y = root.winfo_y()
        window.geometry("+%d+%d" % (x + 200, y + 200))

        menubar = Menu(window)
        window.config(menu=menubar)
        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Search", command=find_itemid)
        #menubar.add_cascade(label="Manually add item", menu=helpmenu)
        padding_lab1 = Label(window, text=" ")
        padding_lab1.pack()

        but_open1 = Button(window, text="Grab Data 1", command=lambda:load_temp_save(1))
        but_open1.pack()
        s1_label = Label(window, text="Quantity:")
        s1_label.pack()
        q1_ent = Entry(window, borderwidth=5, width=3, validate="key", validatecommand=vcmd)
        q1_ent.pack()

        but_open2 = Button(window, text="Grab Data 2", command=lambda:load_temp_save(2))
        but_open2.pack()
        s2_label = Label(window, text="Quantity:")
        s2_label.pack()
        q2_ent = Entry(window, borderwidth=5, width=3, validate="key", validatecommand=vcmd)
        q2_ent.pack()

        but_open3 = Button(window, text="Grab Data 3", command=lambda:load_temp_save(3))
        but_open3.pack()
        s3_label = Label(window, text="Quantity:")
        s3_label.pack()
        q3_ent = Entry(window, borderwidth=5, width=3, validate="key", validatecommand=vcmd)
        q3_ent.pack()

        padding_lab2 = Label(window, text=" ")
        padding_lab2.pack()

        but_search = Button(window, text="Search", command=search)
        but_search.pack()

        help_text = "\n\n----- HOW TO -----\n\n1. Go in-game and note the quantity of the item you are trying to find. \n2. Exit to main menu and enter the quantity in the Manager.\n3. Click grab data 1.\n4. Go back in-game and load into the save file.\n5. Drop some of the items so the quantity is different from the original.\n6. Exit to main menu again.\n7. Enter the new quantity and click grab data 2.\n8. Repeat the process for #3.\n9. Click Search.\n\nNOTE: You must be using the first character in your save file!\n"
        help_lab = Label(window, text=help_text)
        help_lab.pack()

        post_but = Button(window, text="Watch Video", command=lambda: callback(custom_search_tutorial_url))
        post_but.pack()


    def remove_id():

        def done():
            name = fetch_listbox_entry(lb1)[1].strip()
            if len(name) < 1:
                return
            try:
                config.delete_custom_id(name)
            except Exception as e:
                popup(f"Error: Unable to delete Item\n\n{repr(e)}")
            idwin.destroy()
            popupwin.destroy()
            inventory_editor_menu()

        idwin = Toplevel(root)
        idwin.title("Remove Custom ID")
        # popupwin.geometry("200x70")

        x = root.winfo_x()
        y = root.winfo_y()
        idwin.geometry("+%d+%d" % (x + 200, y + 200))


        lb1 = Listbox(idwin, borderwidth=3, width=15, height=10, exportselection=0)
        lb1.config(font=bolded)
        lb1.grid(row=0, column=0, padx=(0,0), pady=(20, 20))
        for i in config.cfg["custom_ids"]:
            lb1.insert(END, "  " + i)

        but_done = Button(idwin, text="Delete", borderwidth=5, width=6, command=done)
        but_done.grid(row=1, column=0, sticky='w', padx=(100,0), pady=(0,15))
        but_cancel = Button(idwin, text="Cancel", borderwidth=5, width=6, command=lambda: idwin.destroy())
        but_cancel.grid(row=1, column=0, sticky='w', padx=(200,100), pady=(0,15))

    def replace_menu():
        def populate_items(*args):
            global itemdb


            cat = cat_vars.get()
            itemdb = itemdata.Items()
            items = itemdb.get_item_ls(cat)

            dropdown3["menu"].delete(0, "end")  # remove full list
            for i in items:
                if len(i) > 1:
                    dropdown3["menu"].add_command(label=i, command=TKIN._setit(i_vars, i))
            i_vars.set("Items")  # default value set
            char = c_vars.get()


        def populate_inventory():
            inv_lb.delete(0,END)
            char = c_vars.get()  # "1. charname"
            if char == "Character" or char == "":
                popup("Character not selected", parent_window=win)
                return


            if char.split(".")[1] == " ":
                popup(
                    "Can't write to empty slot.\nGo in-game and create a character to overwrite.", parent_window=win
                )
                return

            name = fetch_listbox_entry(lb1)[0]  # Save file name. EX: main
            if len(name) < 1:
                popup(text="Slot not selected", parent_window=win)
                return

            dest_file = managed_save_path(name)
            char_ind = int(char.split(".")[0])

            try:
                inventory_items = hexedit.get_inventory(dest_file, char_ind)
            except Exception:
                popup("Unable to load inventory! Do you have Tarnished's Wizened Finger?", parent_window=win)
                return
            for item in inventory_items:
                inv_lb.insert(END, "  " + item["name"])

            # Main GUI content STAT


        def replace_item():

            item = i_vars.get()
            if item == "Items" or item == "":
                popup("Select an item first.", parent_window=win)
                return

            char = c_vars.get()  # "1. charname"
            if char == "Character" or char == "":
                popup("Character not selected", parent_window=win)
                return


            if char.split(".")[1] == " ":
                popup(
                    "Can't write to empty slot.\nGo in-game and create a character to overwrite.", parent_window=win
                )
                return


            item_to_replace = fetch_listbox_entry(inv_lb)[1].lstrip()
            if item_to_replace == "":
                popup("Select an item to replace!", parent_window=win)
                return


            name = fetch_listbox_entry(lb1)[1].strip()  # Save file name. EX: main
            if len(name) < 1:
                popup(text="Slot not selected", parent_window=win)
                return

            dest_file = managed_save_path(name)
            char_ind = int(char.split(".")[0])
            archive_file(dest_file, name, f"ACTION: Replaced {item_to_replace}", get_charnames(dest_file))

            inventory_entries = hexedit.get_inventory(dest_file, char_ind)

            itemid = itemdb.db[cat_vars.get()].get(item)

            for entry in inventory_entries:
                if entry["name"] == item_to_replace:

                    hexedit.overwrite_item(dest_file,char_ind, entry, itemid)
                    popup(f"Successfully replaced {item_to_replace}", parent_window=win)
                    inv_lb.delete(0,END)
                    return




        popupwin.destroy()
        win = Toplevel(root)
        win.title("Replace Items")
        win.resizable(width=True, height=True)
        win.geometry("610x540")
        x = root.winfo_x()
        y = root.winfo_y()
        win.geometry("+%d+%d" % (x + 200, y + 200))

        menubar = Menu(win)
        win.config(menu=menubar)
        helpmenu = Menu(menubar, tearoff=0)
        message = "This feature is experimental and may not work for everything!\n\n-Weapons/Armor is unsupported\n\n-You should try to replace an item with another of the same category ex: crafting materials\n\n-Try not to replace an item you already have, or you will get two stacks of the same item\n\n-Not all items will appear in the inventory box, only detected items that can be overwritten\n\nYou must have Tarnished's Wizened Finger in your inventory (First item you pickup)\n"
        helpmenu.add_command(label="Readme", command=lambda:popup(message, parent_window=win))
        menubar.add_cascade(label="Help", menu=helpmenu)

        # MAIN SAVE FILE LISTBOX
        lb1 = Listbox(win, borderwidth=3, width=15, height=10, exportselection=0)
        lb1.config(font=bolded, width=20)
        lb1.grid(row=1, column=0, padx=(10, 0), pady=(10, 10))
        load_listbox(lb1)

        # SELECT LISTBOX ITEM BUTTON
        but_select1 = Button(
            win, text="Select", command=lambda: get_char_names(lb1, dropdown1, c_vars)
        )
        # but_select1.config(bg='grey', fg='white')
        but_select1.grid(row=2, column=0, padx=(10, 0), pady=(0, 0))

        # CHARACTER DROPDOWN MENU
        opts = [""]
        c_vars = StringVar(win)
        c_vars.set("Character")
        dropdown1 = OptionMenu(win, c_vars, *opts)
        dropdown1.grid(row=3, column=0, padx=(10, 0), pady=(0, 0))


        # LABEL REPLACE WITH
        repl_lab = Label(win, text="Replace with:")
        repl_lab.grid(row=4, column=1)

        # CATEGORY DROPDOWN
        opts1 = itemdb.categories
        cat_vars = StringVar(win)
        cat_vars.set("Category")
        dropdown2 = OptionMenu(win, cat_vars, *opts1)
        dropdown2.config(width=15)

        cat_vars.trace("w", populate_items)
        dropdown2.grid(row=5, column=1, padx=(10, 0), pady=(0, 0))

        # ITEM DROPDOWN
        opts2 = [""]
        i_vars = StringVar(win)
        i_vars.set("Items")
        dropdown3 = OptionMenu(win, i_vars, *opts2)
        dropdown3.config(width=15)
        dropdown3.grid(row=6, column=1, padx=(10, 0), pady=(0, 0))

        but_replace = Button(win, text="Replace", command=replace_item)
        but_replace.grid(row=7, column=1, padx=(10,0), pady=(50,10))

        # inventory items listbox
        inv_lb = Listbox(win, borderwidth=3, width=15, height=10, exportselection=0)
        inv_lb.config(font=bolded, width=25)
        inv_lb.grid(row=1, column=2, padx=(10, 10), pady=(10, 10))

        # get inventory button
        but_get_inv = Button(win, text="Get Inventory", command=populate_inventory )
        but_get_inv.grid(row=2, column=2, padx=(10, 0), pady=(10, 10))












    # Main GUI content STAT
    popupwin = Toplevel(root)
    popupwin.title("Inventory Editor")
    popupwin.resizable(width=True, height=True)
    popupwin.geometry("640x660")
    popupwin.configure(bg=main_window.PALETTE["bg"])
    popupwin.grid_columnconfigure(0, weight=1)

    vcmd = (popupwin.register(validate), "%P")

    bolded = FNT.Font(weight="bold")  # will use the default font

    x = root.winfo_x()
    y = root.winfo_y()
    popupwin.geometry("+%d+%d" % (x + 200, y + 200))

    menubar = Menu(popupwin)
    popupwin.config(menu=menubar)
    helpmenu = Menu(menubar, tearoff=0)
    helpmenu.add_command(label="Replace item", command=replace_menu)
    helpmenu.add_command(label="Search", command=manual_search)
    helpmenu.add_command(label="Add item by ID", command=add_custom_id)
    helpmenu.add_command(label="Remove Custom Item", command=remove_id)
    helpmenu.add_command(label="View Master Spreadsheet", command=lambda:webbrowser.open_new_tab("https://github.com/RorikSR/ER_Save_Manager_v2/blob/main/ALL_ITEM_IDS.md"))
    menubar.add_cascade(label="Actions", menu=helpmenu)

    main_window.label(
        popupwin,
        "Inventory Editor",
        role="section",
        bg=main_window.PALETTE["bg"],
        font=("Segoe UI", 15, "bold"),
    ).grid(row=0, column=0, padx=(38, 0), pady=(18, 4), sticky="w")
    main_window.label(
        popupwin,
        "Pick a managed profile, select a character, then filter the DLC/base item catalog by name.",
        role="small",
        bg=main_window.PALETTE["bg"],
        wraplength=555,
    ).grid(row=1, column=0, padx=(38, 0), pady=(0, 18), sticky="w")

    main_window.label(
        popupwin,
        "1. Managed profile",
        role="body",
        bg=main_window.PALETTE["bg"],
    ).grid(row=2, column=0, padx=(155, 0), pady=(0, 6), sticky="w")

    # MAIN SAVE FILE LISTBOX
    lb1 = main_window.listbox(popupwin, width=28, height=10, exportselection=0)
    lb1.config(font=bolded)
    lb1.grid(row=3, column=0, padx=(155, 0), pady=(0, 12), sticky="w")
    load_listbox(lb1)

    # SELECT LISTBOX ITEM BUTTON
    but_select1 = main_window.button(
        popupwin, text="Select", command=lambda: get_char_names(lb1, dropdown1, c_vars)
    )
    # but_select1.config(bg='grey', fg='white')
    but_select1.grid(row=4, column=0, padx=(155, 0), pady=(0, 14), sticky="w")

    main_window.label(
        popupwin,
        "2. Character",
        role="body",
        bg=main_window.PALETTE["bg"],
    ).grid(row=5, column=0, padx=(155, 0), pady=(0, 6), sticky="w")

    # CHARACTER DROPDOWN MENU
    opts = [""]
    c_vars = StringVar(popupwin)
    c_vars.set("Character")
    dropdown1 = OptionMenu(popupwin, c_vars, *opts)
    dropdown1.config(width=25)
    dropdown1.grid(row=6, column=0, padx=(155, 0), pady=(0, 12), sticky="w")

    main_window.label(
        popupwin,
        "3. Category and item",
        role="body",
        bg=main_window.PALETTE["bg"],
    ).grid(row=7, column=0, padx=(155, 0), pady=(0, 6), sticky="w")

    # CATEGORY DROPDOWN
    opts1 = itemdb.categories
    cat_vars = StringVar(popupwin)
    cat_vars.set("Category")
    dropdown2 = OptionMenu(popupwin, cat_vars, *opts1)
    dropdown2.config(width=25)

    cat_vars.trace("w", populate_items)
    dropdown2.grid(row=8, column=0, padx=(155, 0), pady=(0, 10), sticky="w")

    # ITEM SEARCH
    item_search_var = StringVar(popupwin)
    item_search_var.trace("w", refresh_items)
    item_search_lab = main_window.label(popupwin, text="Search:", role="small", bg=main_window.PALETTE["bg"])
    item_search_lab.grid(row=9, column=0, padx=(105, 0), pady=(0, 10), sticky="w")
    item_search_ent = main_window.entry(popupwin, width=28, textvariable=item_search_var)
    item_search_ent.grid(row=9, column=0, padx=(155, 0), pady=(0, 10), sticky="w")

    # ITEM DROPDOWN
    opts2 = [""]
    i_vars = StringVar(popupwin)
    i_vars.set("Items")
    dropdown3 = OptionMenu(popupwin, i_vars, *opts2)
    dropdown3.config(width=25)
    dropdown3.grid(row=10, column=0, padx=(155, 0), pady=(0, 10), sticky="w")

    qty_lab = main_window.label(popupwin, text="Qty:", role="small", bg=main_window.PALETTE["bg"])
    qty_lab.grid(row=10, column=0, padx=(395, 0), pady=(0, 10), sticky="w")
    qty_ent = Entry(
        popupwin, borderwidth=5, width=4, validate="key", validatecommand=vcmd
    )
    qty_ent.grid(row=10, column=0, padx=(430, 0), pady=(0, 10), sticky="w")

    # SELECT LISTBOX ITEM BUTTON
    but_set = main_window.button(popupwin, text="Apply quantity", command=add, variant="primary")
    but_set.config(font=bolded)
    but_set.grid(row=11, column=0, padx=(155, 0), pady=(16, 10), sticky="w")

    main_window.label(
        popupwin,
        "Note: this editor changes quantities for items already present in the selected inventory.",
        role="small",
        bg=main_window.PALETTE["bg"],
        wraplength=520,
    ).grid(row=12, column=0, padx=(38, 0), pady=(10, 18), sticky="w")


def recovery_menu():
    def do_popup(event):
        try:
            rt_click_menu.tk_popup(
                event.x_root, event.y_root
            )  # Grab x,y position of mouse cursor
        finally:
            rt_click_menu.grab_release()



    def recover():
        name = fetch_listbox_entry(lb1)[1].strip().replace(" ", "__").replace(":", ".")
        if len(name) < 1:
            popup("\nNothing selected!\n")
            return
        path = f"./data/archive/{name}/ER0000.xz"
        folder_path = f"./data/recovered/{name}/"

        try:
            unarchive_file(path)
            recovered_file = str(Path(folder_path) / ext())
            popup("Succesfully recovered save file.\nImport now?", functions=(lambda:import_save_menu(directory=recovered_file), donothing), buttons=True, button_names=("Yes", "No"))
        except FileNotFoundError as e:
            popup(e)


    def pop_up(txt, bold=True):
        """Basic popup window used only for parent function"""
        pwin = Toplevel(win)
        pwin.title("Manager")
        lab = Label(pwin, text=txt)
        if bold is True:
            lab.config(font=bolded)
        lab.grid(row=0, column=0, padx=15, pady=15, columnspan=2)
        x = win.winfo_x()
        y = win.winfo_y()
        pwin.geometry("+%d+%d" % (x + 200, y + 200))

    def delete_entry(directory):

        def delete(directory):
            delete_folder(directory)
            selected_index = lb1.curselection()
            if selected_index:
                lb1.delete(selected_index)
            win.update()

        def dont_delete():
            pass

        popup("Are you sure?", parent_window=win, functions=(lambda:delete(directory),dont_delete), buttons=True)

    def delete_all():
        folder_path = "./data/archive/"
        shutil.rmtree(folder_path)
        os.makedirs(folder_path)
        lb1.delete(0,END)

    win = Toplevel(root)
    win.title("Recovery")
    win.resizable(width=True, height=True)
    win.geometry("530x640")


    #bolded = FNT.Font(weight="bold")  # will use the default font

    x = root.winfo_x()
    y = root.winfo_y()
    win.geometry("+%d+%d" % (x + 200, y + 200))

    menubar = Menu(win)
    win.config(menu=menubar)
    helpmenu = Menu(menubar, tearoff=0)
    helpmenu.add_command(
        label="Readme",
        command=lambda: pop_up(
            """\u2022 This tool recovers save files in case of user error.\n
                \u2022 Every time you modify/create/delete a save file, before the action is performed, a copy is created, compressed and stored in data/archive.\n
                \u2022 The original file size of 28mb is compressed to 2mb. To recover a file, simply select a file and click Restore.\n
                \u2022 Restored save files are in the data/recovered directory.\n
                \u2022 Right-click on a save in the listbox to get additional file info.
                """
        ),
    )
    helpmenu.add_command(label="Delete All", command=lambda:popup(text="Are you sure?", buttons=True, functions=(delete_all, donothing)))
    menubar.add_cascade(label="File", menu=helpmenu)




    # LISTBOX
    lb1 = Listbox(win, borderwidth=3, width=32, height=25, exportselection=0)
    lb1.config(font=bolded)
    lb1.grid(row=1, column=0, padx=(120, 0), pady=(35, 15))
    if os.path.isdir("./data/archive/") is True:
        lb1.delete(0, END)
        entries = sorted(PATH("./data/archive/").iterdir(), key=os.path.getmtime)

        for entry in reversed(entries):
            lb1.insert(END, "  " + str(entry).replace("\\", "/").split("archive/")[1].replace("__", " ").replace(".", ":"))

    rt_click_menu = Menu(lb1, tearoff=0)
    rt_click_menu.add_command(label="Get Info", command=lambda:grab_metadata(f"./data/archive/{fetch_listbox_entry(lb1)[1].strip()}/info.txt"   )  )

    rt_click_menu.add_command(label="Delete", command=lambda:delete_entry
    (f"./data/archive/{fetch_listbox_entry(lb1)[1].strip().replace(' ', '__').replace(':', '.')}/"))
    lb1.bind("<Button-3>", do_popup)



    # SELECT LISTBOX ITEM BUTTON
    but_select1 = Button(win, text="Recover", command=recover)
    but_select1.grid(row=2, column=0, padx=(120, 0), pady=(0, 10))


def seamless_coop_menu():
    def set_mode(enabled):
        config.set("seamless-coop", enabled)
        refresh_dashboard()

    x = lambda: 'Enabled' if config.cfg['seamless-coop'] else 'Disabled'
    popup(f"Enable this option to support the seamless Co-op mod .co2 extension\nIt's recommended to use a separate copy of the Manager just for seamless co-op.\n\nCurrent State: {x()}", buttons=True, button_names=("Enable", "Disable"), functions=(lambda:set_mode(True), lambda:set_mode(False)))


def set_playtimes_menu():
    #  This function is unused. The game will overwrite modified playtime value on reload with original value.
    def set():
        choice = char_vars.get()
        try:
            choice_real = choice.split(". ")[1]
        except IndexError:
            popup("Select a character!")
            return
        slot_ind = int(choice.split(".")[0])
        if len(hr_ent.get()) < 1 or len(min_ent.get()) < 1 or len(sec_ent.get()) < 1:
            popup("Set a value for hr/min/sec")
            return
        time = [hr_ent.get(), min_ent.get(), sec_ent.get()]
        archive_file(path, choice_real, "ACTION: Change Play Time", names)
        hexedit.set_play_time(path,slot_ind,time)
        popup("Success")

    def validate_hr(P):
        if len(P) > 0 and len(P) < 5 and P.isdigit():
            return True
        else:
            return False

    def validate_min_sec(P):
        if len(P) > 0 and len(P) < 3 and P.isdigit() and int(P) < 61:
            return True
        else:
            return False



    name = fetch_listbox_entry(lb)[0]
    if name == "":
        popup("No listbox item selected.")
        return
    path = managed_save_path(name)
    names = get_charnames(path)
    if names is False:
        popup("FileNotFoundError: This is a known issue.\nPlease try re-importing your save file.")


    chars = []
    for ind, i in enumerate(names):
        if i != None:
            chars.append(f"{ind +1}. {i}")




    rwin = Toplevel(root)
    rwin.title("Set Play Time")
    rwin.geometry("200x250")

    vcmd_hr = (rwin.register(validate_hr), "%P")
    vcmd_min_sec = (rwin.register(validate_min_sec), "%P")

    bolded = FNT.Font(weight="bold")  # will use the default font
    x = root.winfo_x()
    y = root.winfo_y()
    rwin.geometry("+%d+%d" % (x + 250, y + 200))

    opts = chars
    char_vars = StringVar(rwin)
    char_vars.set("Character")

    drop = OptionMenu(rwin, char_vars, *opts)
    drop.grid(row=0, column=0, padx=(15, 0), pady=(15, 0))
    drop.configure(width=20)

    hr_lab = Label(rwin, text="Hours: ")
    hr_lab.grid(row=1, column=0, padx=(15,0), pady=(15,0), sticky="w")
    hr_ent = Entry(rwin, borderwidth=5, width=5, validate="key", validatecommand=vcmd_hr)
    hr_ent.grid(row=1, column=0, padx=(70, 0), pady=(15, 0))

    min_lab = Label(rwin, text="Minutes: ")
    min_lab.grid(row=2, column=0, padx=(15,0), pady=(15,0), sticky="w")
    min_ent = Entry(rwin, borderwidth=5, width=5, validate="key", validatecommand=vcmd_min_sec)
    min_ent.grid(row=2, column=0, padx=(70, 0), pady=(15, 0))

    sec_lab = Label(rwin, text="Seconds: ")
    sec_lab.grid(row=3, column=0, padx=(15,0), pady=(15,0), sticky="w")
    sec_ent = Entry(rwin, borderwidth=5, width=5, validate="key", validatecommand=vcmd_min_sec)
    sec_ent.grid(row=3, column=0, padx=(70, 0), pady=(15, 0))

    but_go = Button(rwin, text="Set", borderwidth=5, command=set)
    but_go.config(font=bolded)
    but_go.grid(row=4, column=0, padx=(15, 0), pady=(20, 0))


def set_starting_class_menu():
    def set():
        if class_var.get() == "Class":
            popup("No class selected!")
            return
        if char_var.get() == "Character":
            popup("No Character Selected!")
            return
        src_ind = int(char_var.get().split(".")[0])
        selected_name = char_var.get().split(".")[1]
        archive_file(path, name, f"Modified starting class of {selected_name}", names)
        hexedit.set_starting_class(path,src_ind,class_var.get())
        popup("Success!")
        return

    # Populate dropdown containing characters.
    name = fetch_listbox_entry(lb)[0]
    if name == "":
        popup("No listbox item selected.")
        return
    path = managed_save_path(name)
    names = get_charnames(path)
    if names is False:
        popup("FileNotFoundError: This is a known issue.\nPlease try re-importing your save file.")

    chars = []
    for ind, i in enumerate(names):
        if i != None:
            chars.append(f"{ind +1}. {i}")




    rwin = Toplevel(root)
    rwin.title("Set Starting Class")
    rwin.geometry("200x190")

    bolded = FNT.Font(weight="bold")  # will use the default font
    x = root.winfo_x()
    y = root.winfo_y()
    rwin.geometry("+%d+%d" % (x + 250, y + 200))

    opts = chars
    char_var = StringVar(rwin)
    char_var.set("Character")

    drop = OptionMenu(rwin, char_var, *opts)
    drop.grid(row=0, column=0, padx=(15, 0), pady=(15, 0))
    drop.configure(width=20)

    class_opts = ["Vagabond", "Warrior", "Hero", "Bandit", "Astrologer", "Prophet", "Confessor", "Samurai", "Prisoner", "Wretch"]
    class_var = StringVar(rwin)
    class_var.set("Class")

    class_drop = OptionMenu(rwin, class_var, *class_opts)
    class_drop.grid(row=1, column=0, padx=(15, 0), pady=(15, 0))



    but_set = Button(rwin, text="Set", borderwidth=5, command=set)
    but_set.config(font=bolded)
    but_set.grid(row=4, column=0, padx=(15, 0), pady=(20, 0))


def change_default_steamid_menu():


    def done():
        s_steam_id_val = ent.get()
        if not len(s_steam_id_val) == 17:
            popup("SteamID should be 17 digits long")
            return
        config.set("steamid", s_steam_id_val)


        popup("Successfully changed default SteamID")
        popupwin.destroy()

    def cancel():
        popupwin.destroy()

    def validate(P):
        if len(P) == 0:
            return True
        elif len(P) < 18 and P.isdigit():
            return True
        else:
            # Anything else, reject it
            return False

    popupwin = Toplevel(root)
    popupwin.title("Set SteamID")
    vcmd = (popupwin.register(validate), "%P")
    # popupwin.geometry("200x70")

    s_id = config.cfg["steamid"]
    lab = Label(popupwin, text=f"Current ID: {s_id}\nEnter new ID:")
    lab.grid(row=0, column=0)
    ent = Entry(popupwin, borderwidth=5, validate="key", validatecommand=vcmd)
    ent.grid(row=1, column=0, padx=25, pady=10)
    x = root.winfo_x()
    y = root.winfo_y()
    popupwin.geometry("+%d+%d" % (x + 200, y + 200))
    but_done = Button(popupwin, text="Done", borderwidth=5, width=6, command=done)
    but_done.grid(row=2, column=0, padx=(25, 65), pady=(0, 15), sticky="w")
    but_cancel = Button(popupwin, text="Cancel", borderwidth=5, width=6, command=cancel)
    but_cancel.grid(row=2, column=0, padx=(70, 0), pady=(0, 15))


def import_save_menu(directory=False):
    """Opens file explorer to choose a save file to import, Then checks if the files steam ID matches users, and replaces it with users id"""

    if os.path.isdir(savedir) is False:
        os.makedirs(savedir)
    if directory:
        d = directory
    else:
        d = fd.askopenfilename()

    if len(d) < 1:
        return

    if not (d.endswith(".sl2") or d.endswith(".co2")):
        popup("Select a valid save file!\nIt should be named: ER0000.sl2 or ER0000.co2 if seamless co-op is enabled.")
        return




    def cancel():
        popupwin.destroy()

    def done():

        name = ent.get().strip()
        if len(name) < 1:
            popup("No name entered.")
            return
        isforbidden = False
        for char in name:
            if char in "~'{};:./\\,:*?<>|-!@#$%^&()+":
                isforbidden = True
        if isforbidden is True:
            popup("Forbidden character used")
            return
        elif isforbidden is False:
            entries = []
            for entry in os.listdir(savedir):
                entries.append(entry)
            if name.replace(" ", "-") in entries:
                popup("Name already exists")
                return







        names = get_charnames(d)
        archive_file(d, name, "ACTION: Imported", names)

        newdir = "{}{}/".format(savedir, name.replace(" ", "-"))
        cp_to_saves_cmd = lambda: savefile_io.copy_save_to_directory(d, newdir, target_filename=ext())

        if os.path.isdir(newdir) is False:
            cmd_out = run_command(lambda: os.makedirs(newdir))

            if cmd_out[0] == "error":
                print("---ERROR #1----")
                return

            lb.insert(END, "  " + name)
            cmd_out = run_command(cp_to_saves_cmd)
            if cmd_out[0] == "error":
                return
            create_notes(name, "{}{}/".format(savedir, name.replace(" ", "-")))

            imported_path = resolve_save_path(newdir)
            file_id = hexedit.get_id(imported_path)
            user_id = config.cfg["steamid"]
            if len(user_id) < 17:
                popupwin.destroy()
                popup("Please configure your SteamID in Edit > Change Default SteamID before importing saves.")
                return
            if file_id != int(user_id):
                popup(
                    f"File SteamID: {file_id}\nYour SteamID: {user_id}", buttons=True, button_names=("Patch with your ID", "Leave it"), b_width=(15,8), functions=(lambda:hexedit.replace_id(imported_path, int(user_id)), donothing)
                )
                #hexedit.replace_id(f"{newdir}/ER0000.sl2", int(steam_id_val))

            popupwin.destroy()



    popupwin = Toplevel(root)
    popupwin.title("Import")
    # popupwin.geometry("200x70")
    lab = Label(popupwin, text="Enter a Name:")
    lab.grid(row=0, column=0)
    ent = Entry(popupwin, borderwidth=5)
    ent.grid(row=1, column=0, padx=25, pady=10)
    x = root.winfo_x()
    y = root.winfo_y()
    popupwin.geometry("+%d+%d" % (x + 200, y + 200))
    but_done = Button(popupwin, text="Done", borderwidth=5, width=6, command=done)
    but_done.grid(row=2, column=0, padx=(25, 65), pady=(0, 15), sticky="w")
    but_cancel = Button(popupwin, text="Cancel", borderwidth=5, width=6, command=cancel)
    but_cancel.grid(row=2, column=0, padx=(70, 0), pady=(0, 15))


def godmode_menu():
    def get_char_names(lstbox, drop, v):
        """Populates dropdown menu containing the name of characters in a save file"""
        v.set("Character")
        name = fetch_listbox_entry(lstbox)[0]
        if len(name) < 1:
            return
        file = managed_save_path(name)
        names = get_charnames(file)
        if names is False:
            popup("FileNotFoundError: This is a known issue.\nPlease try re-importing your save file.")
        drop["menu"].delete(0, "end")  # remove full list

        index = 1
        for ind, opt in enumerate(names):
            if not opt is None:
                opt = f"{index}. {opt}"
                drop["menu"].add_command(label=opt, command=TKIN._setit(v, opt))
                index += 1
            elif opt is None:
                opt = f"{ind + 1}. "
                drop["menu"].add_command(label=opt, command=TKIN._setit(v, opt))
                index += 1



    def run_cheat():

        char = c_vars.get()  # "1. charname"
        if char == "Character" or char == "":
            popup("Character not selected", parent_window=popupwin)
            return

        if char.split(".")[1] == " ":
            popup("Can't write to empty slot.\nGo in-game and create a character to overwrite.", parent_window=popupwin)
            return



        name = fetch_listbox_entry(lb1)[0]  # Save file name. EX: main
        if len(name) < 1:
            popup(text="Slot not selected", parent_window=popupwin)
            return

        dest_file = managed_save_path(name)
        char_ind = int(char.split(".")[0])

        archive_file(dest_file, name, "ACTION: CHEAT GOD-MODE", get_charnames(dest_file))
        try:
            hexedit.set_attributes(dest_file, char_ind, [99, 99, 99], cheat=True)
            popup("Success!", parent_window=popupwin)
        except Exception as e:
            #traceback.print_exc()
            #str_err = "".join(traceback.format_exc())
            #popup(str_err, parent_window=popupwin)
            popup("Unable to aquire stats/level.\nYour character level may be incorrect.\nFix now?",functions=(lambda:fix_stats_menu(dest_file, char_ind), lambda:popupwin.destroy()), buttons=True, button_names=("Yes", "No"), parent_window=popupwin)



    popupwin = Toplevel(root)
    popupwin.title("God Mode")
    popupwin.resizable(width=True, height=True)
    popupwin.geometry("510x470")

    x = root.winfo_x()
    y = root.winfo_y()
    popupwin.geometry("+%d+%d" % (x + 200, y + 200))

    main_label = Label(popupwin, text="DO NOT use this feature online! You will most certainly get banned.\n\nThis will set your HP,ST,FP to 60,000\n\n Note: Your stats will return to normal after leveling up or equipping a stat boosting item. \n\nNote: Remove any stat boosting gear from your character before doing this or it won't work.\n\n")
    main_label.pack()

    # MAIN SAVE FILE LISTBOX
    lb1 = Listbox(popupwin, borderwidth=3, width=15, height=10, exportselection=0)
    lb1.config(font=bolded)
    lb1.pack()
    load_listbox(lb1)

    but_select1 = Button( popupwin, text="Select", command=lambda: get_char_names(lb1, dropdown1, c_vars))
    but_select1.pack()

    # CHARACTER DROPDOWN MENU
    opts = [""]
    c_vars = StringVar(popupwin)
    c_vars.set("Character")
    dropdown1 = OptionMenu(popupwin, c_vars, *opts)
    dropdown1.pack()


    # SELECT LISTBOX ITEM BUTTON
    but_set = Button(popupwin, text="Set", command=run_cheat)
    but_set.config(font=bolded)
    but_set.pack()


def fix_stats_menu(dest_file, char_ind):
    def validate(P):
        if len(P) == 0:
            return True
        elif len(P) < 3 and P.isdigit() and int(P) > 0:
            return True
        else:
            # Anything else, reject it
            return False

    def fix():
        for entry in entries:
            if len(entry.get()) < 1:
                popup("Not all stats entered!",parent_window=popupwin)
                return

        stat_lst = [int(i.get()) for i in entries]

        name = dest_file.split("/")[-2]
        print(f"DEST: {dest_file}   ==  char_ind {char_ind} ---   {stat_lst}")
        archive_file(dest_file, name, "ACTION: Fix Level", get_charnames(dest_file))
        x = hexedit.fix_stats(dest_file, char_ind, stat_lst)
        if x is True:
            popup("Successfully found stats and patched level!", parent_window=popupwin)
        elif x is False:
            popup("Unable to find stats, ensure you entered your stats correctly.\nMake sure your stats aren't boosted by an item.", parent_window=popupwin)
            return


    # Main GUI content STAT
    popupwin = Toplevel(root)
    popupwin.title("Fix Level")
    popupwin.resizable(width=True, height=True)
    popupwin.geometry("580x550")
    vcmd = (popupwin.register(validate), "%P")
    bolded = FNT.Font(weight="bold")  # will use the default font
    x = root.winfo_x()
    y = root.winfo_y()
    popupwin.geometry("+%d+%d" % (x + 200, y + 200))



    main_label = Label(popupwin, text="Enter your character stats.\n\nGo in-game and remove any stat boosting gear and take note of your stats and enter them here:")
    main_label.grid(row=0, column=0, padx=(20,0), pady=(5,0), sticky="n")

    # VIGOR
    vig_lab = Label(popupwin, text="VIGOR:")
    vig_lab.config(font=bolded)
    vig_lab.grid(row=0, column=0, padx=(20, 0), pady=(75, 0), sticky="n")

    vig_ent = Entry( popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd)
    vig_ent.grid(row=0, column=0, padx=(120, 0), pady=(75, 0), sticky="n")

    # MIND
    mind_lab = Label(popupwin, text="MIND:")
    mind_lab.config(font=bolded)
    mind_lab.grid(row=0, column=0, padx=(20, 0), pady=(115, 0), sticky="n")

    mind_ent = Entry(popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd)
    mind_ent.grid(row=0, column=0, padx=(120, 0), pady=(115, 0), sticky="n")

    # ENDURANCE
    end_lab = Label(popupwin, text="END:")
    end_lab.config(font=bolded)
    end_lab.grid(row=0, column=0, padx=(20, 0), pady=(155, 0), sticky="n")

    end_ent = Entry(popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd)
    end_ent.grid(row=0, column=0, padx=(120, 0), pady=(155, 0), sticky="n")

    # STRENGTH
    str_lab = Label(popupwin, text="STR:")
    str_lab.config(font=bolded)
    str_lab.grid(row=0, column=0, padx=(20, 0), pady=(195, 0), sticky="n")

    str_ent = Entry(popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd)
    str_ent.grid(row=0, column=0, padx=(120, 0), pady=(195, 0), sticky="n")

    # DEXTERITY
    dex_lab = Label(popupwin, text="DEX:")
    dex_lab.config(font=bolded)
    dex_lab.grid(row=0, column=0, padx=(20, 0), pady=(235, 0), sticky="n")

    dex_ent = Entry(popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd)
    dex_ent.grid(row=0, column=0, padx=(120, 0), pady=(235, 0), sticky="n")

    # INTELLIGENCE
    int_lab = Label(popupwin, text="INT:")
    int_lab.config(font=bolded)
    int_lab.grid(row=0, column=0, padx=(20, 0), pady=(275, 0), sticky="n")

    int_ent = Entry(popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd)
    int_ent.grid(row=0, column=0, padx=(120, 0), pady=(275, 0), sticky="n")

    # FAITH
    fai_lab = Label(popupwin, text="FAITH:")
    fai_lab.config(font=bolded)
    fai_lab.grid(row=0, column=0, padx=(20, 0), pady=(315, 0), sticky="n")

    fai_ent = Entry(popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd)
    fai_ent.grid(row=0, column=0, padx=(120, 0), pady=(315, 0), sticky="n")

    # ARCANE
    arc_lab = Label(popupwin, text="ARC:")
    arc_lab.config(font=bolded)
    arc_lab.grid(row=0, column=0, padx=(20, 0), pady=(355, 0), sticky="n")

    arc_ent = Entry(popupwin, borderwidth=5, width=3, validate="key", validatecommand=vcmd)
    arc_ent.grid(row=0, column=0, padx=(120, 0), pady=(355, 0), sticky="n")

    # lIST OF ALL ENTRIES
    entries = [vig_ent, mind_ent, end_ent, str_ent, dex_ent, int_ent, fai_ent, arc_ent]



    # SET STATS BUTTON
    but_set_stats = Button(popupwin, text="Fix", width=12, command=fix)
    but_set_stats.config(font=bolded)
    but_set_stats.grid(row=0, column=0, padx=(25, 0), pady=(420, 0), sticky="n")


def set_runes_menu():
    def get_char_names(lstbox, drop, v):
        """Populates dropdown menu containing the name of characters in a save file"""
        v.set("Character")
        name = fetch_listbox_entry(lstbox)[0]
        if len(name) < 1:
            return
        file = managed_save_path(name)
        names = get_charnames(file)
        if names is False:
            popup("FileNotFoundError: This is a known issue.\nPlease try re-importing your save file.")
        drop["menu"].delete(0, "end")  # remove full list

        index = 1
        for ind, opt in enumerate(names):
            if not opt is None:
                opt = f"{index}. {opt}"
                drop["menu"].add_command(label=opt, command=TKIN._setit(v, opt))
                index += 1
            elif opt is None:
                opt = f"{ind + 1}. "
                drop["menu"].add_command(label=opt, command=TKIN._setit(v, opt))
                index += 1

    def validate(P):

        if P.isdigit():
            return True
        else:
            return False


    def set_runecount():
        old_quantity = old_q_ent.get()
        new_quantity = new_q_ent.get()

        char = c_vars.get()  # "1. charname"
        if char == "Character" or char == "":
            popup("Character not selected", parent_window=popupwin)
            return

        if char.split(".")[1] == " ":
            popup("Can't write to empty slot.\nGo in-game and create a character to overwrite.", parent_window=popupwin)
            return



        name = fetch_listbox_entry(lb1)[0]  # Save file name. EX: main
        if len(name) < 1:
            popup(text="Slot not selected", parent_window=popupwin)
            return

        dest_file = managed_save_path(name)
        char_ind = int(char.split(".")[0])

        if old_quantity == "" or new_quantity == "":
            popup("Enter a rune quantity", parent_window = popupwin)
            return

        if int(old_quantity) < 1000 or int(new_quantity) < 1000:
            popup("Rune count is too low! Enter a value greater than 1000", parent_window=popupwin)
            return
        if int(new_quantity) > 999999999: # Max quantity in-game
            new_quantity = 999999999


        archive_file(dest_file, fetch_listbox_entry(lb1)[0], "ACTION: Set rune count", get_charnames(dest_file))
        out = hexedit.set_runes(dest_file, char_ind, int(old_quantity), int(new_quantity))
        if out is False:
            popup("Unable to find rune count!\nMake sure you have a larger value with the number being fairly random. Ex: 85732", parent_window=popupwin)
            return
        else:
            popup(f"Successfully set rune count to {new_quantity}", parent_window=popupwin)

    popupwin = Toplevel(root)
    popupwin.title("Set Rune Count")
    popupwin.resizable(width=True, height=True)
    popupwin.geometry("510x590")

    x = root.winfo_x()
    y = root.winfo_y()
    popupwin.geometry("+%d+%d" % (x + 200, y + 200))
    vcmd = (popupwin.register(validate), "%P")


    main_label = Label(popupwin, text="Go in-game and take note of how many held runes the character has.\nBigger numbers ensure the program finds the proper location of your runes.\n")
    main_label.pack()

    # MAIN SAVE FILE LISTBOX
    lb1 = Listbox(popupwin, borderwidth=3, width=15, height=10, exportselection=0)
    lb1.config(font=bolded)

    lb1.pack()
    load_listbox(lb1)

    but_select1 = Button( popupwin, text="Select", command=lambda: get_char_names(lb1, dropdown1, c_vars))
    but_select1.pack()

    # CHARACTER DROPDOWN MENU
    opts = [""]
    c_vars = StringVar(popupwin)
    c_vars.set("Character")
    dropdown1 = OptionMenu(popupwin, c_vars, *opts)
    dropdown1.pack()

    padding_lab1 = Label(popupwin, text="\n\n")
    padding_lab1.pack()

    # OLD QUANTITY LABEL
    old_q_label = Label(popupwin, text="Enter Current rune count:")
    old_q_label.pack()

     # OLD QUANTITY ENTRY
    old_q_ent = Entry(popupwin, borderwidth=5, validate="key", validatecommand=vcmd)
    old_q_ent.pack()


     # NEW QUANTITY LABEL
    new_q_label = Label(popupwin, text="Enter new rune count:")
    new_q_label.pack()

     # NEW QUANTITY ENTRY
    new_q_ent = Entry(popupwin, borderwidth=5, validate="key", validatecommand=vcmd)
    new_q_ent.pack()


    padding_lab3 = Label(popupwin, text="\n\n")
    padding_lab3.pack()

    # SET BUTTON
    but_set = Button(popupwin, text="Set", command=set_runecount)
    but_set.config(font=bolded)
    but_set.pack()



# //// LEGACY FUNCTIONS (NO LONGER USED) ////

def quick_restore():
    """Copies the selected save file in temp to selected listbox item"""
    lst_box_choice = fetch_listbox_entry(lb)[0]
    if len(lst_box_choice) < 1:
        popup("No listbox item selected.")
        return
    src = f"./data/temp/{lst_box_choice}"
    dest = f"{savedir}{lst_box_choice}"
    file = resolve_save_path(dest)
    archive_file(file,lst_box_choice, "ACTION: Quick Restore", get_charnames(file))
    cmd = lambda: copy_folder(src, dest)
    x = run_command(cmd)
    if x[0] != "error":
        popup("Successfully restored backup.")


def quick_backup():
    """Creates a backup of selected listbox item to temp folder"""
    lst_box_choice = fetch_listbox_entry(lb)[0]
    if len(lst_box_choice) < 1:
        popup("No listbox item selected.")
        return

    src = f"{savedir}{lst_box_choice}"
    dest = f"./data/temp/{lst_box_choice}"
    cmd = lambda: copy_folder(src, dest)
    x = run_command(cmd)
    if x[0] != "error":
        popup("Successfully created backup.")


def save_backup():
    """Quickly save a backup of the current game save. Used from the menubar."""
    gamedir = config.cfg.get("gamedir", "")
    if len(gamedir) < 2:
        popup("Set your Default Game Directory first")
        return
    comm = lambda: copy_folder(gamedir, backupdir)

    if os.path.isdir(backupdir) is False:
        cmd_out1 = run_command(lambda: os.makedirs(backupdir))
        if cmd_out1[0] == "error":
            return
    cmd_out2 = run_command(comm)
    if cmd_out2[0] == "error":
        return
    else:
        popup("Backup saved successfully")


def load_backup():
    """Quickly load a backup of the current game save. Used from the menubar."""
    gamedir = config.cfg.get("gamedir", "")
    if len(gamedir) < 2:
        popup("Set your Default Game Directory first")
        return
    comm = lambda: copy_folder(backupdir, gamedir)
    if os.path.isdir(backupdir) is False:
        run_command(lambda: os.makedirs(backupdir))

    if len(re.findall(r"\d{17}", str(os.listdir(backupdir)))) < 1:
        popup("No backup found")

    else:
        popup("Overwrite existing save?", command=comm, buttons=True)


def create_notes(name, dir):
    """Create a notepad document in specified save slot. (Currently disabled)"""
    return


def about():
    popup(
        text=(
            "ER Save Manager v2\n"
            "Maintainer: RorikSR\n"
            "GitHub: github.com/RorikSR/ER_Save_Manager_v2\n\n"
            "Based on prior community work by ClayAmore and Ariescyn."
        )
    )


def open_notes():
    name = fetch_listbox_entry(lb)[0]
    if len(name) < 1:
        popup("No listbox item selected.")
        return
    cmd = lambda: open_textfile_in_editor(f"{savedir}{name}/notes.txt")
    out = run_command(cmd)


def _format_bool(value):
    return "OK" if value else "Needs attention"


def _current_save_path_or_none():
    if "config" not in globals() or len(config.cfg.get("gamedir", "")) < 2:
        return None
    try:
        path = PATH(game_save_path())
    except Exception:
        return None
    return path if path.exists() else None


def _latest_backup_path():
    backup_root = savefile_io.BACKUP_ROOT
    if not backup_root.exists():
        return None
    backups = [path for path in backup_root.rglob("*") if path.is_file() and path.suffix.lower() in (".sl2", ".co2")]
    if not backups:
        return None
    return max(backups, key=lambda path: path.stat().st_mtime)


def _safe_md5(path):
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inspect_save(path):
    path = PATH(path)
    data = path.read_bytes()
    checksum_result = checksum_logic.verify_data(data)
    names = get_charnames(str(path))
    if names is False:
        names = []
    active_names = [name for name in names if name]
    expected_size = checksum_logic.GENERAL_DATA_END
    return {
        "path": path,
        "exists": path.exists(),
        "extension": path.suffix.lower(),
        "size": path.stat().st_size,
        "expected_size": expected_size,
        "size_ok": path.stat().st_size >= expected_size,
        "checksum": checksum_result,
        "slot_count": checksum_logic.SLOT_COUNT,
        "characters": active_names,
        "md5": _safe_md5(path),
    }


def refresh_dashboard():
    if "dashboard_vars" not in globals():
        return

    mode_name = "Seamless Co-op (.co2)" if config.cfg.get("seamless-coop") else "Vanilla (.sl2)"
    dashboard_vars["mode"].set(mode_name)
    dashboard_vars["steamid"].set(config.cfg.get("steamid") or "Not set")
    dashboard_vars["folder"].set(config.cfg.get("gamedir") or "Not set")

    latest_backup = _latest_backup_path()
    dashboard_vars["backup"].set(latest_backup.name if latest_backup else "No backups yet")

    path = _current_save_path_or_none()
    if path is None:
        dashboard_vars["checksum"].set("No current save detected")
        return

    try:
        inspection = _inspect_save(path)
        dashboard_vars["checksum"].set(_format_bool(inspection["checksum"]["valid"]))
    except Exception:
        dashboard_vars["checksum"].set("Unable to inspect")


def verify_save_menu():
    path = _current_save_path_or_none()
    if path is None:
        popup("Set your default game directory first, or make sure ER0000.sl2 / ER0000.co2 exists there.")
        return

    try:
        inspection = _inspect_save(path)
    except Exception:
        popup("Unable to verify save:\n\n" + traceback.format_exc())
        return

    issues = inspection["checksum"]["issues"]
    characters = inspection["characters"]
    issue_text = "None" if not issues else "\n".join(
        f"- {issue['kind']} {issue.get('slot', '')}: expected {issue['expected']}, actual {issue['actual']}"
        for issue in issues[:6]
    )
    if len(issues) > 6:
        issue_text += f"\n- ... {len(issues) - 6} more"

    message = (
        f"Save file:\n{inspection['path']}\n\n"
        f"Extension: {inspection['extension']}\n"
        f"Size: {inspection['size']:,} bytes ({'expected range' if inspection['size_ok'] else 'smaller than expected'})\n"
        f"Checksum: {_format_bool(inspection['checksum']['valid'])}\n"
        f"Slots scanned: {inspection['slot_count']}\n"
        f"Characters found: {len(characters)}\n"
        f"MD5: {inspection['md5']}\n\n"
        f"Characters:\n{chr(10).join(characters) if characters else 'No named characters detected'}\n\n"
        f"Checksum issues:\n{issue_text}"
    )
    popup(message, title="Verify Save")
    refresh_dashboard()


def backup_browser_menu():
    backup_root = savefile_io.BACKUP_ROOT
    backups = []
    if backup_root.exists():
        backups = sorted(
            [path for path in backup_root.rglob("*") if path.is_file() and path.suffix.lower() in (".sl2", ".co2")],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

    win = Toplevel(root)
    win.title("Backup Browser")
    win.geometry("760x460")
    win.configure(bg=main_window.PALETTE["bg"])

    main_window.label(
        win,
        "Backup Browser",
        role="section",
        bg=main_window.PALETTE["bg"],
        font=("Segoe UI", 15, "bold"),
    ).pack(anchor="w", padx=22, pady=(18, 4))
    main_window.label(
        win,
        "Restore a timestamped backup into your current game save directory. A backup of the current save is created first.",
        role="small",
        bg=main_window.PALETTE["bg"],
        wraplength=700,
    ).pack(anchor="w", padx=22, pady=(0, 12))

    content = Frame(win, bg=main_window.PALETTE["bg"])
    content.pack(fill=BOTH, expand=True, padx=22, pady=(0, 18))

    backup_lb = main_window.listbox(content, width=78, height=14, exportselection=0)
    backup_lb.pack(fill=BOTH, expand=True)

    details_var = StringVar(value="Select a backup to see details.")
    main_window.label(
        content,
        "",
        role="small",
        textvariable=details_var,
        bg=main_window.PALETTE["bg"],
        wraplength=700,
    ).pack(anchor="w", pady=(10, 8))

    for path in backups:
        rel = path.relative_to(backup_root)
        timestamp = datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        backup_lb.insert(END, f"  {timestamp}  |  {rel}")

    if not backups:
        backup_lb.insert(END, "  No backups found yet.")

    def selected_backup():
        if not backups or len(backup_lb.curselection()) < 1:
            return None
        index = backup_lb.curselection()[0]
        if index >= len(backups):
            return None
        return backups[index]

    def show_details(*args):
        path = selected_backup()
        if path is None:
            return
        current = _current_save_path_or_none()
        current_md5 = _safe_md5(current) if current else "No current save"
        details_var.set(
            f"Backup: {path.name} | Size: {path.stat().st_size:,} bytes | MD5: {_safe_md5(path)} | Current MD5: {current_md5}"
        )

    def restore_selected():
        backup = selected_backup()
        if backup is None:
            popup("Select a backup first.", parent_window=win)
            return
        current = _current_save_path_or_none()
        if current is None:
            popup("Set your default game directory first.", parent_window=win)
            return

        def do_restore():
            savefile_io.prepare_for_write(current, label="before_restore")
            shutil.copy2(backup, current)
            verify = checksum_logic.verify_data(current.read_bytes())
            refresh_dashboard()
            if verify["valid"]:
                popup("Backup restored and checksum is valid.", parent_window=win)
            else:
                popup("Backup restored, but checksum verification reported issues.", parent_window=win)

        popup(
            f"Restore this backup over the current game save?\n\n{backup}",
            functions=(do_restore, donothing),
            buttons=True,
            parent_window=win,
        )

    backup_lb.bind("<<ListboxSelect>>", show_details)

    actions = Frame(content, bg=main_window.PALETTE["bg"])
    actions.pack(fill=X, pady=(6, 0))
    main_window.button(actions, "Restore selected", command=restore_selected, variant="primary").pack(side=LEFT)
    main_window.button(actions, "Open backups folder", command=lambda: open_folder_standard_exporer(str(backup_root))).pack(side=LEFT, padx=(10, 0))
    main_window.button(actions, "Close", command=win.destroy).pack(side=RIGHT)


def convert_save_menu():
    source = fd.askopenfilename(
        title="Select Elden Ring save",
        filetypes=(("Elden Ring saves", "*.sl2 *.co2"), ("All files", "*.*")),
    )
    if not source:
        return

    source_path = PATH(source)
    if source_path.suffix.lower() not in (".sl2", ".co2"):
        popup("Select a valid .sl2 or .co2 save file.")
        return

    target_extension = ".co2" if source_path.suffix.lower() == ".sl2" else ".sl2"
    target = fd.asksaveasfilename(
        title=f"Save converted {target_extension} file",
        initialdir=str(source_path.parent),
        initialfile=f"{source_path.stem}{target_extension}",
        defaultextension=target_extension,
        filetypes=((f"Elden Ring {target_extension}", f"*{target_extension}"), ("All files", "*.*")),
    )
    if not target:
        return

    output = PATH(target)
    if output.suffix.lower() != target_extension:
        output = output.with_suffix(target_extension)

    try:
        if output.exists():
            savefile_io.prepare_for_write(output, label="before_convert_overwrite")
        shutil.copy2(source_path, output)
        recalculated = checksum_logic.recalculate_data(output.read_bytes())
        output.write_bytes(recalculated)
        verify = checksum_logic.verify_data(recalculated)
    except Exception:
        popup("Unable to convert save:\n\n" + traceback.format_exc())
        return

    status = "valid" if verify["valid"] else "has checksum issues"
    popup(f"Converted save created:\n{output}\n\nChecksum: {status}", title="Save Converter")
    refresh_dashboard()


def inventory_pro_menu():
    rows = inventory_tools.catalog_rows()
    filtered_rows = []

    win = Toplevel(root)
    win.title("Inventory Pro")
    win.geometry("1020x650")
    win.configure(bg=main_window.PALETTE["bg"])

    main_window.label(
        win,
        "Inventory Pro",
        role="section",
        bg=main_window.PALETTE["bg"],
        font=("Segoe UI", 16, "bold"),
    ).pack(anchor="w", padx=22, pady=(18, 4))
    main_window.label(
        win,
        "Search the full base game + DLC catalog, then scan a real save to find known, unknown, duplicate and suspicious entries.",
        role="small",
        bg=main_window.PALETTE["bg"],
        wraplength=930,
    ).pack(anchor="w", padx=22, pady=(0, 14))

    controls = Frame(win, bg=main_window.PALETTE["bg"])
    controls.pack(fill=X, padx=22, pady=(0, 10))

    search_var = StringVar()
    game_var = StringVar(value="All")
    status_var = StringVar(value=f"{len(rows)} catalog items loaded.")

    main_window.label(controls, "Search", role="small", bg=main_window.PALETTE["bg"]).pack(side=LEFT, padx=(0, 8))
    search_entry = main_window.entry(controls, width=34, textvariable=search_var)
    search_entry.pack(side=LEFT, padx=(0, 12))
    main_window.label(controls, "Source", role="small", bg=main_window.PALETTE["bg"]).pack(side=LEFT, padx=(0, 8))
    source_menu = OptionMenu(controls, game_var, "All", "Base Game", "DLC", "Custom", "Unknown")
    source_menu.config(width=12)
    source_menu.pack(side=LEFT, padx=(0, 12))

    table_frame = Frame(win, bg=main_window.PALETTE["bg"])
    table_frame.pack(fill=BOTH, expand=True, padx=22, pady=(0, 8))

    style = ttk.Style(win)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "Inventory.Treeview",
        background=main_window.PALETTE["entry"],
        fieldbackground=main_window.PALETTE["entry"],
        foreground=main_window.PALETTE["text"],
        rowheight=24,
        borderwidth=0,
    )
    style.configure(
        "Inventory.Treeview.Heading",
        background=main_window.PALETTE["card_alt"],
        foreground=main_window.PALETTE["text"],
        relief="flat",
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Inventory.Treeview",
        background=[("selected", main_window.PALETTE["accent_dark"])],
        foreground=[("selected", "#fff6e8")],
    )

    columns = ("category", "game", "goods_id", "raw_item", "ids")
    tree = ttk.Treeview(table_frame, columns=columns, show="tree headings", height=18, style="Inventory.Treeview")
    tree.heading("#0", text="Item")
    tree.heading("category", text="Category")
    tree.heading("game", text="Source")
    tree.heading("goods_id", text="Goods ID")
    tree.heading("raw_item", text="Raw")
    tree.heading("ids", text="IDs")
    tree.column("#0", width=310, anchor="w")
    tree.column("category", width=180, anchor="w")
    tree.column("game", width=90, anchor="w")
    tree.column("goods_id", width=105, anchor="e")
    tree.column("raw_item", width=115, anchor="e")
    tree.column("ids", width=80, anchor="w")
    tree.pack(side=LEFT, fill=BOTH, expand=True)

    scrollbar = Scrollbar(table_frame, orient=VERTICAL, command=tree.yview)
    scrollbar.pack(side=RIGHT, fill=Y)
    tree.configure(yscrollcommand=scrollbar.set)

    def row_matches(row):
        query = search_var.get().strip().lower()
        source = game_var.get()
        if source != "All" and row["game"] != source:
            return False
        if not query:
            return True
        haystack = " ".join(
            [
                row["name"],
                row["category"],
                row["source"],
                str(row["goods_id"]),
                str(row["raw_item"]),
                ",".join(str(part) for part in row["ids"]),
            ]
        ).lower()
        return query in haystack

    def refresh_table(*args):
        nonlocal filtered_rows
        filtered_rows = [row for row in rows if row_matches(row)]
        tree.delete(*tree.get_children())
        for index, row in enumerate(filtered_rows[:1500]):
            tree.insert(
                "",
                END,
                iid=str(index),
                text=row["name"],
                values=(
                    row["category"],
                    row["game"],
                    row["goods_id"],
                    row["raw_item"],
                    f"{row['ids'][0]}, {row['ids'][1]}",
                ),
            )
        status_var.set(f"{len(filtered_rows)} matching item(s).")

    def selected_row():
        selection = tree.selection()
        if not selection:
            return None
        index = int(selection[0])
        if index >= len(filtered_rows):
            return None
        return filtered_rows[index]

    def copy_selected_id():
        row = selected_row()
        if row is None:
            popup("Select an item first.", parent_window=win)
            return
        win.clipboard_clear()
        win.clipboard_append(str(row["goods_id"]))
        status_var.set(f"Copied Goods ID {row['goods_id']} for {row['name']}.")

    def export_catalog():
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output = PATH(data_path("reports", f"catalog_export_{timestamp}.json"))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        popup(f"Catalog exported:\n{output}", parent_window=win)

    def scan_current_save():
        save_path = _current_save_path_or_none()
        if save_path is None:
            popup("Set your default game directory first, or make sure the current ER0000 save exists.", parent_window=win)
            return

        try:
            report = inventory_tools.scan_save_inventory(save_path)
            json_path, md_path = inventory_tools.write_inventory_scan_report(report)
        except Exception:
            popup("Inventory scan failed:\n\n" + traceback.format_exc(), parent_window=win)
            return

        summary = report["summary"]
        message = (
            f"Inventory scan complete.\n\n"
            f"Known entries: {summary['known']}\n"
            f"Unknown entries: {summary['unknown']}\n"
            f"DLC entries: {summary['dlc']}\n"
            f"Duplicate groups: {summary['duplicates']}\n"
            f"Rare entries: {summary['rare']}\n\n"
            f"JSON:\n{json_path}\n\nMarkdown:\n{md_path}"
        )
        popup(message, title="Inventory Scan", parent_window=win)
        status_var.set(f"Last scan: {summary['known']} known, {summary['unknown']} unknown.")

    search_var.trace("w", refresh_table)
    game_var.trace("w", refresh_table)
    refresh_table()
    search_entry.focus_set()

    footer = Frame(win, bg=main_window.PALETTE["bg"])
    footer.pack(fill=X, padx=22, pady=(4, 18))
    main_window.label(footer, "", role="small", textvariable=status_var, bg=main_window.PALETTE["bg"]).pack(side=LEFT)
    main_window.button(footer, "Copy Goods ID", command=copy_selected_id).pack(side=RIGHT, padx=(8, 0))
    main_window.button(footer, "Export catalog", command=export_catalog).pack(side=RIGHT, padx=(8, 0))
    main_window.button(footer, "Scan current save", command=scan_current_save, variant="primary").pack(side=RIGHT, padx=(8, 0))
    main_window.button(footer, "Edit quantities", command=quantity_editor_menu, variant="primary").pack(side=RIGHT, padx=(8, 0))


def quantity_editor_menu():
    save_path = _current_save_path_or_none()
    if save_path is None:
        popup("Set your default game directory first, or make sure the current ER0000 save exists.")
        return

    names = hexedit.get_names(str(save_path))
    character_options = [
        f"{index}. {name}"
        for index, name in enumerate(names, start=1)
        if name
    ]
    if not character_options:
        popup("No named characters were found in the current save.")
        return

    inventory_rows = []
    filtered_rows = []

    win = Toplevel(root)
    win.title("Quantity Editor")
    win.geometry("980x660")
    win.configure(bg=main_window.PALETTE["bg"])

    main_window.label(
        win,
        "Quantity Editor",
        role="section",
        bg=main_window.PALETTE["bg"],
        font=("Segoe UI", 16, "bold"),
    ).pack(anchor="w", padx=22, pady=(18, 4))
    main_window.label(
        win,
        "Load a character inventory, select an object, then increase, decrease or set the exact quantity. Backups and checksum recalculation run automatically.",
        role="small",
        bg=main_window.PALETTE["bg"],
        wraplength=920,
    ).pack(anchor="w", padx=22, pady=(0, 14))

    controls = Frame(win, bg=main_window.PALETTE["bg"])
    controls.pack(fill=X, padx=22, pady=(0, 10))

    char_var = StringVar(value=character_options[0])
    search_var = StringVar()
    exact_qty_var = StringVar(value="")
    status_var = StringVar(value=f"Current save: {save_path.name}")

    main_window.label(controls, "Character", role="small", bg=main_window.PALETTE["bg"]).pack(side=LEFT, padx=(0, 8))
    character_menu = OptionMenu(controls, char_var, *character_options)
    character_menu.config(width=24)
    character_menu.pack(side=LEFT, padx=(0, 12))
    main_window.label(controls, "Search", role="small", bg=main_window.PALETTE["bg"]).pack(side=LEFT, padx=(0, 8))
    search_entry = main_window.entry(controls, width=30, textvariable=search_var)
    search_entry.pack(side=LEFT, padx=(0, 12))

    table_frame = Frame(win, bg=main_window.PALETTE["bg"])
    table_frame.pack(fill=BOTH, expand=True, padx=22, pady=(0, 8))

    style = ttk.Style(win)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "Quantity.Treeview",
        background=main_window.PALETTE["entry"],
        fieldbackground=main_window.PALETTE["entry"],
        foreground=main_window.PALETTE["text"],
        rowheight=24,
        borderwidth=0,
    )
    style.configure(
        "Quantity.Treeview.Heading",
        background=main_window.PALETTE["card_alt"],
        foreground=main_window.PALETTE["text"],
        relief="flat",
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Quantity.Treeview",
        background=[("selected", main_window.PALETTE["accent_dark"])],
        foreground=[("selected", "#fff6e8")],
    )

    columns = ("quantity", "category", "game", "goods_id", "raw_item")
    tree = ttk.Treeview(table_frame, columns=columns, show="tree headings", height=18, style="Quantity.Treeview")
    tree.heading("#0", text="Item")
    tree.heading("quantity", text="Qty")
    tree.heading("category", text="Category")
    tree.heading("game", text="Source")
    tree.heading("goods_id", text="Goods ID")
    tree.heading("raw_item", text="Raw")
    tree.column("#0", width=320, anchor="w")
    tree.column("quantity", width=90, anchor="e")
    tree.column("category", width=190, anchor="w")
    tree.column("game", width=90, anchor="w")
    tree.column("goods_id", width=110, anchor="e")
    tree.column("raw_item", width=120, anchor="e")
    tree.pack(side=LEFT, fill=BOTH, expand=True)

    scrollbar = Scrollbar(table_frame, orient=VERTICAL, command=tree.yview)
    scrollbar.pack(side=RIGHT, fill=Y)
    tree.configure(yscrollcommand=scrollbar.set)

    def selected_slot():
        return int(char_var.get().split(".", 1)[0])

    def selected_row():
        selection = tree.selection()
        if not selection:
            return None
        index = int(selection[0])
        if index >= len(filtered_rows):
            return None
        return filtered_rows[index]

    def row_matches(row):
        query = search_var.get().strip().lower()
        if not query:
            return True
        haystack = " ".join(
            [
                row["name"],
                row["category"],
                row["game"],
                str(row["quantity"]),
                str(row["goods_id"]),
                str(row["raw_item"]),
            ]
        ).lower()
        return query in haystack

    def refresh_table(*args):
        nonlocal filtered_rows
        filtered_rows = [row for row in inventory_rows if row_matches(row)]
        tree.delete(*tree.get_children())
        for index, row in enumerate(filtered_rows):
            tree.insert(
                "",
                END,
                iid=str(index),
                text=row["name"],
                values=(
                    row["quantity"],
                    row["category"],
                    row["game"],
                    row["goods_id"],
                    row["raw_item"],
                ),
            )
        status_var.set(f"{len(filtered_rows)} visible item(s), {len(inventory_rows)} total loaded.")

    def load_inventory(*args):
        nonlocal inventory_rows
        try:
            inventory_rows = inventory_tools.inventory_rows_for_slot(save_path, selected_slot())
        except Exception:
            popup("Unable to load inventory:\n\n" + traceback.format_exc(), parent_window=win)
            inventory_rows = []
        refresh_table()

    def apply_quantity(new_quantity):
        row = selected_row()
        if row is None:
            popup("Select an item first.", parent_window=win)
            return

        new_quantity = max(0, int(new_quantity))
        if new_quantity == 0:
            confirm_text = f"Set {row['name']} quantity to 0?"
        else:
            confirm_text = f"Set {row['name']} quantity to {new_quantity}?"

        def do_apply():
            try:
                result = inventory_tools.set_inventory_quantity(
                    save_path,
                    selected_slot(),
                    row["raw_item"],
                    new_quantity,
                    index=row["index"],
                )
            except Exception:
                popup("Unable to update quantity:\n\n" + traceback.format_exc(), parent_window=win)
                return

            if not result["updated"]:
                popup("Unable to find that item in the selected character inventory.", parent_window=win)
                return

            if result["checksum"] and not result["checksum"]["valid"]:
                popup("Quantity updated, but checksum verification reported issues.", parent_window=win)
            else:
                status_var.set(f"Updated {row['name']} to {new_quantity}. Checksum OK.")
            refresh_dashboard()
            load_inventory()

        popup(confirm_text, functions=(do_apply, donothing), buttons=True, parent_window=win)

    def adjust_selected(delta):
        row = selected_row()
        if row is None:
            popup("Select an item first.", parent_window=win)
            return
        apply_quantity(max(0, row["quantity"] + delta))

    def set_exact():
        value = exact_qty_var.get().strip()
        if not value.isdigit():
            popup("Enter a valid quantity.", parent_window=win)
            return
        apply_quantity(int(value))

    search_var.trace("w", refresh_table)
    char_var.trace("w", load_inventory)

    footer = Frame(win, bg=main_window.PALETTE["bg"])
    footer.pack(fill=X, padx=22, pady=(4, 18))
    main_window.label(footer, "", role="small", textvariable=status_var, bg=main_window.PALETTE["bg"]).pack(side=LEFT)

    main_window.button(footer, "-10", command=lambda: adjust_selected(-10)).pack(side=RIGHT, padx=(6, 0))
    main_window.button(footer, "-1", command=lambda: adjust_selected(-1)).pack(side=RIGHT, padx=(6, 0))
    main_window.button(footer, "+1", command=lambda: adjust_selected(1), variant="primary").pack(side=RIGHT, padx=(6, 0))
    main_window.button(footer, "+10", command=lambda: adjust_selected(10), variant="primary").pack(side=RIGHT, padx=(6, 0))
    main_window.button(footer, "Set exact", command=set_exact).pack(side=RIGHT, padx=(12, 0))
    exact_entry = main_window.entry(footer, width=8, textvariable=exact_qty_var)
    exact_entry.pack(side=RIGHT, padx=(6, 0))

    load_inventory()
    search_entry.focus_set()










# ///// MAIN GUI CONTENT /////


def do_popup(event):
    try:
        rt_click_menu.tk_popup(
            event.x_root, event.y_root
        )  # Grab x,y position of mouse cursor
    finally:
        rt_click_menu.grab_release()


def main():
    global root, bg_img, background, done_img, load_save_img, delete_save_img
    global menubar, filemenu, editmenu, toolsmenu, cheatmenu, helpmenu
    global create_save_lab, cr_save_ent, but_go, lb, bolded, rt_click_menu
    global but_load_save, but_delete_save, config, itemdb, save_count_var, main_status_var, dashboard_vars

    root = main_window.create_root("{} {}".format(app_title, version), geometry="980x700")
    try:
        root.iconbitmap(icon_file)
    except Exception:
        print("Unix doesn't support .ico - setting the background as app icon")
        root.iconphoto(True, PhotoImage(background_img))

    bg_img = ImageTk.PhotoImage(image=Image.open(background_img))
    background = Label(root, image=bg_img)
    background.place(x=bk_p[0], y=bk_p[1], relwidth=1, relheight=1)

    config = Config()
    itemdb = itemdata.Items()
    if not os.path.exists("./data/save-files"):
        os.makedirs("./data/save-files")

    menubar = Menu(root)
    root.config(menu=menubar)

    filemenu = Menu(menubar, tearoff=0)
    filemenu.add_command(label="Import Save File", command=import_save_menu)
    filemenu.add_command(label="Seamless Co-op Mode", command=seamless_coop_menu)
    filemenu.add_command(label="Open Default Game Save Directory", command=open_game_save_dir)
    filemenu.add_command(label="Force quit Elden Ring", command=forcequit)
    filemenu.add_separator()
    filemenu.add_command(label="Donate", command=lambda:webbrowser.open_new_tab("https://www.paypal.com/donate/?hosted_button_id=H2X24U55NUJJW"))
    filemenu.add_command(label="Exit", command=root.quit)
    menubar.add_cascade(label="File", menu=filemenu)

    editmenu = Menu(menubar, tearoff=0)
    editmenu.add_command(label="Change Default Directory", command=change_default_dir)
    editmenu.add_command(label="Change Default SteamID", command=change_default_steamid_menu)
    if not NEXUS_BUILD:
        editmenu.add_command(label="Check for updates", command=update_app)
    menubar.add_cascade(label="Edit", menu=editmenu)

    toolsmenu = Menu(menubar, tearoff=0)
    toolsmenu.add_command(label="Character Manager", command=char_manager_menu)
    toolsmenu.add_command(label="Stat Editor", command=stat_editor_menu)
    toolsmenu.add_command(label="Set Starting Class", command=set_starting_class_menu)
    toolsmenu.add_command(label="Inventory Editor", command=inventory_editor_menu)
    toolsmenu.add_command(label="Inventory Pro", command=inventory_pro_menu)
    toolsmenu.add_command(label="Quantity Editor", command=quantity_editor_menu)
    toolsmenu.add_command(label="File Recovery", command=recovery_menu)
    toolsmenu.add_separator()
    toolsmenu.add_command(label="Verify Current Save", command=verify_save_menu)
    toolsmenu.add_command(label="Backup Browser", command=backup_browser_menu)
    toolsmenu.add_command(label="Convert .sl2 / .co2", command=convert_save_menu)
    menubar.add_cascade(label="Tools", menu=toolsmenu)

    cheatmenu = Menu(menubar, tearoff=0)
    cheatmenu.add_command(label="God Mode", command=godmode_menu)
    cheatmenu.add_command(label="Set Runes", command=set_runes_menu)
    menubar.add_cascade(label="Cheats", menu=cheatmenu)

    helpmenu = Menu(menubar, tearoff=0)
    helpmenu.add_command(label="Watch Video", command=lambda: webbrowser.open_new_tab(video_url))
    helpmenu.add_command(label="Changelog", command=lambda:changelog(run=True))
    helpmenu.add_command(label="Report Bug", command=lambda:popup("Report bugs on Nexus, GitHub or email me at scyntacks94@gmail.com"))
    menubar.add_cascade(label="Help", menu=helpmenu)

    shell = Frame(root, bg=main_window.PALETTE["bg"])
    shell.place(relx=0.5, rely=0.5, anchor=CENTER, width=930, height=640)

    header = Frame(shell, bg=main_window.PALETTE["bg"])
    header.pack(fill=X, pady=(0, 16))
    main_window.label(
        header,
        "Elden Ring Save Manager",
        role="title",
        bg=main_window.PALETTE["bg"],
    ).pack(anchor="w")
    mode_name = "Seamless Co-op (.co2)" if config.cfg.get("seamless-coop") else "Vanilla (.sl2)"
    main_window.label(
        header,
        f"Profiles, backups, inventory tools and checksum-safe edits for Shadow of the Erdtree. Active mode: {mode_name}",
        role="subtitle",
        bg=main_window.PALETTE["bg"],
    ).pack(anchor="w", pady=(4, 0))

    dashboard_vars = {
        "mode": StringVar(value="Checking..."),
        "steamid": StringVar(value="Checking..."),
        "folder": StringVar(value="Checking..."),
        "backup": StringVar(value="Checking..."),
        "checksum": StringVar(value="Checking..."),
    }
    dashboard = main_window.card(shell)
    dashboard.pack(fill=X, pady=(0, 14), ipady=8)
    dashboard.grid_columnconfigure(0, weight=1)
    dashboard.grid_columnconfigure(1, weight=1)
    dashboard.grid_columnconfigure(2, weight=2)
    dashboard.grid_columnconfigure(3, weight=1)
    dashboard.grid_columnconfigure(4, weight=1)

    dashboard_items = (
        ("Mode", "mode"),
        ("SteamID", "steamid"),
        ("Save Folder", "folder"),
        ("Last Backup", "backup"),
        ("Checksum", "checksum"),
    )
    for index, (title, key) in enumerate(dashboard_items):
        cell = Frame(dashboard, bg=main_window.PALETTE["card"])
        cell.grid(row=0, column=index, sticky="ew", padx=(14 if index == 0 else 4, 14 if index == 4 else 4), pady=8)
        main_window.label(cell, title, role="small").pack(anchor="w")
        main_window.label(
            cell,
            "",
            role="body",
            textvariable=dashboard_vars[key],
            wraplength=230 if key == "folder" else 140,
        ).pack(anchor="w")

    body = Frame(shell, bg=main_window.PALETTE["bg"])
    body.pack(fill=BOTH, expand=True)

    left_card = main_window.card(body)
    left_card.pack(side=LEFT, fill=BOTH, padx=(0, 16), ipadx=18, ipady=12)

    right_card = main_window.card(body)
    right_card.pack(side=LEFT, fill=BOTH, expand=True, ipadx=22, ipady=18)

    main_window.label(left_card, "Quick Actions", role="section").pack(anchor="w", padx=20, pady=(14, 2))
    main_window.label(
        left_card,
        "Create a named profile from your current game save, then load it back whenever you need it.",
        role="small",
        wraplength=275,
    ).pack(anchor="w", padx=20, pady=(0, 12))

    create_save_lab = main_window.label(left_card, "New profile name", role="body")
    create_save_lab.pack(anchor="w", padx=20, pady=(0, 6))

    cr_save_ent = main_window.entry(left_card, width=32)
    cr_save_ent.pack(fill=X, padx=20, pady=(0, 10))

    but_go = main_window.button(left_card, "Create profile from current save", command=create_save, variant="primary")
    but_go.pack(fill=X, padx=20, pady=(0, 14))

    main_window.label(left_card, "Tools", role="section").pack(anchor="w", padx=20, pady=(0, 8))
    main_window.button(left_card, "Character Manager", command=char_manager_menu, pady=7).pack(fill=X, padx=20, pady=3)
    main_window.button(left_card, "Inventory Pro", command=inventory_pro_menu, pady=7, variant="primary").pack(fill=X, padx=20, pady=3)
    main_window.button(left_card, "Quantity Editor", command=quantity_editor_menu, pady=7, variant="primary").pack(fill=X, padx=20, pady=3)
    main_window.button(left_card, "Stat Editor", command=stat_editor_menu, pady=7).pack(fill=X, padx=20, pady=3)
    main_window.button(left_card, "File Recovery", command=recovery_menu, pady=7).pack(fill=X, padx=20, pady=3)

    main_window.label(left_card, "Safety", role="section").pack(anchor="w", padx=20, pady=(14, 8))
    main_window.button(left_card, "Verify current save", command=verify_save_menu, pady=7).pack(fill=X, padx=20, pady=3)
    main_window.button(left_card, "Browse backups", command=backup_browser_menu, pady=7).pack(fill=X, padx=20, pady=3)
    main_window.button(left_card, "Convert .sl2 / .co2", command=convert_save_menu, pady=7).pack(fill=X, padx=20, pady=3)

    list_header = Frame(right_card, bg=main_window.PALETTE["card"])
    list_header.pack(fill=X, padx=20, pady=(18, 8))
    main_window.label(list_header, "Saved Profiles", role="section").pack(side=LEFT)
    save_count_var = StringVar(value="0 profiles ready")
    main_window.label(list_header, "", role="small", textvariable=save_count_var).pack(side=RIGHT)

    lb = main_window.listbox(right_card, width=32, height=17, exportselection=0)
    bolded = FNT.Font(weight="bold")
    lb.config(font=bolded)
    lb.pack(fill=BOTH, expand=True, padx=20, pady=(0, 12))

    rt_click_menu = Menu(lb, tearoff=0)
    rt_click_menu.add_command(label="Rename Save", command=rename_slot)
    rt_click_menu.add_command(label="Rename Characters", command=rename_characters_menu)
    rt_click_menu.add_command(label="Update", command=update_slot)
    rt_click_menu.add_command(label="Change SteamID", command=set_steam_id_menu)
    rt_click_menu.add_command(label="Open File Location", command=open_folder)
    lb.bind("<Button-3>", do_popup)

    load_listbox(lb)
    refresh_dashboard()

    profile_actions = Frame(right_card, bg=main_window.PALETTE["card"])
    profile_actions.pack(fill=X, padx=20, pady=(0, 12))
    but_load_save = main_window.button(
        profile_actions,
        "Load selected profile",
        command=load_save_from_lb,
        variant="primary",
    )
    but_load_save.pack(side=LEFT, fill=X, expand=True, padx=(0, 8))
    but_delete_save = main_window.button(
        profile_actions,
        "Delete",
        command=delete_save,
        variant="danger",
        width=9,
    )
    but_delete_save.pack(side=LEFT)

    main_status_var = StringVar(
        value="Backups are created automatically. Tip: right-click a profile for rename, update, SteamID and folder options."
    )
    main_window.label(
        right_card,
        "",
        role="small",
        textvariable=main_status_var,
        wraplength=455,
    ).pack(anchor="w", padx=20, pady=(0, 18))

    if not NEXUS_BUILD:
        update_app(True)

    if len(config.cfg["steamid"]) != 17:
        popup("SteamID not set. Click edit > Change default SteamID to set.")

    changelog()
    finish_update()
    config.set_update(False)
    root.mainloop()


if __name__ == "__main__":
    main()
