# Elden Ring Save Manager - Shadow of the Erdtree Edition

Save manager and save editor for **Elden Ring** with support for **Shadow of the Erdtree**, vanilla `.sl2` saves, and Seamless Co-op `.co2` saves.

> Unofficial community project. Not affiliated with FromSoftware, Bandai Namco, Seamless Co-op, ClayAmore, or the original project authors.

Current repository: [RorikSR/ER_Save_Manager_v2](https://github.com/RorikSR/ER_Save_Manager_v2)

## Spanish

La documentacion en espanol esta disponible aqui:

- [Guia de uso en espanol](docs/es/USAGE.md)
- [Seguridad y backups en espanol](docs/es/SAFETY.md)
- [Desarrollo en espanol](docs/es/DEVELOPMENT.md)
- [Publicacion en GitHub en espanol](docs/es/PUBLISHING.md)

## Credits And Upstream

This project builds on community knowledge and prior Elden Ring save-editing work.

- Original reference/upstream credit: [ClayAmore/ER-Save-Editor](https://github.com/ClayAmore/ER-Save-Editor)
- Earlier Python save-manager lineage/reference: [Ariescyn/EldenRing-Save-Manager](https://github.com/Ariescyn/EldenRing-Save-Manager)
- See [CREDITS.md](CREDITS.md) and [NOTICE.md](NOTICE.md) before publishing releases or redistributing binaries.
- See [LICENSE](LICENSE) for the current conservative license status.

## Features

- Current-save dashboard: `.sl2/.co2` mode, SteamID, configured save folder, latest backup, and checksum status.
- Safe save verification: extension, file size, characters, slots, MD5, and checksum.
- Seamless Co-op `.co2` support.
- Bidirectional `.sl2` <-> `.co2` conversion.
- Automatic backups before save-modifying operations.
- Checksum recalculation and validation to reduce `Save Data Corrupted` risk.
- External JSON item catalog for base game + DLC items.
- Stats editor, and change starting class.
- Inventory Pro with search by name, category, source, Goods ID, Raw ID, and internal IDs.
- Quantity Editor to view current item quantities and increase, decrease, or set exact values.
- Real inventory scanner with JSON/Markdown reports.
- Backup Browser for reviewing and restoring backups.

## Download

### Windows

The recommended way for end users is to download the executable from **GitHub Releases**.

Release page: [github.com/RorikSR/ER_Save_Manager_v2/releases](https://github.com/RorikSR/ER_Save_Manager_v2/releases)

Expected executable:

```powershell
EldenRingSaveManager.exe
```

On first launch, the executable creates a `data/` folder next to the `.exe` for local settings, backups, reports, and save profiles.

### Linux
See [Run From Source](#run-from-source)

## Quick Start

1. Close Elden Ring before modifying saves.
2. Open `EldenRingSaveManager.exe` (or `run.sh` if on linux).
3. Set your save folder through `Edit > Change Default Directory`.
4. Set your SteamID through `Edit > Change Default SteamID`.
5. If you use Seamless Co-op, enable `File > Seamless Co-op Mode`.
6. Run `Verify current save` before editing.
7. Create a profile with `Create profile from current save`.
8. Use `Inventory Pro` or `Quantity Editor` to inspect or modify inventory.

## Safety

- The app creates backups before write operations.
- Keep your own manual backups anyway.
- Do not edit saves while Elden Ring is running.
- Avoid using modified saves online unless you understand the risks.
- Compatibility with future game versions is not guaranteed.

## Run From Source

Requirements:

- If Windows, then Windows 10/11
- Python 3.11 or newer
- Python with Tcl/Tk support

### Windows

Install dependencies and run:

```powershell
.\run_app.ps1
```

Or manually:

```powershell
python -m pip install -r requirements.txt
python app.py
```

### Linux

Install dependencies (especially tkinter)
then:
```bash
python -m pip install -r requirements.txt
python -m venv .venv
```
> [!NOTE]
> Some distros let you run python bare, while others insist on a sandboxed mode.  Most Arch-based distros are sandboxed.  There are 2 .sh files for this purpose.
```bash
# for barebones
run-bare.sh
```
```bash
# for sandboxed
run-sandboxed.sh
```

## Build Windows Executable

```powershell
.\build_exe.ps1
```

The executable is generated at:

```powershell
dist\EldenRingSaveManager.exe
```

Do not commit `dist/`. Attach the `.exe` as a **GitHub Release** asset instead.

For Nexus Mods, build the offline-safe package:

```powershell
.\build_nexus_package.ps1
```

See [docs/NEXUS_MODS.md](docs/NEXUS_MODS.md) for upload text, tags, permissions, and release notes.

Release notes for the first public build are available in
[docs/RELEASE_NOTES_v1.0.0-sote.md](docs/RELEASE_NOTES_v1.0.0-sote.md).

## Tests

Syntax check:

```powershell
python -m py_compile app.py SaveManager.py hexedit.py itemdata.py savefile_io.py os_layer.py logic\checksum.py logic\hex_editor.py logic\inventory_tools.py gui\main_window.py
```

Checksum tests:

```powershell
python tools\test_checksum.py
```

Inventory scan:

```powershell
python tools\scan_inventory.py
```

## Project Structure

```text
app.py                         Entry point
SaveManager.py                 Legacy/main UI
gui/                           Visual helpers and theme
logic/                         UI-independent logic
data/items/                    JSON item catalogs
tools/                         Validation/import/scan scripts
docs/                          English documentation
docs/es/                       Spanish documentation
```

## Documentation

English:

- [Usage guide](docs/USAGE.md)
- [Development guide](docs/DEVELOPMENT.md)
- [Safety and backups](docs/SAFETY.md)
- [GitHub publishing guide](docs/PUBLISHING.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)
- [Support policy](SUPPORT.md)
- [Security policy](SECURITY.md)

Spanish:

- [Guia de uso](docs/es/USAGE.md)
- [Guia de desarrollo](docs/es/DEVELOPMENT.md)
- [Seguridad y backups](docs/es/SAFETY.md)
- [Publicacion en GitHub](docs/es/PUBLISHING.md)
- [Checklist de release](docs/es/RELEASE_CHECKLIST.md)

## DLC Status

The DLC catalog is loaded from:

```text
data/items/shadow_of_the_erdtree.json
```

Includes support for items such as:

- Scadutree Fragment
- Revered Spirit Ash
- DLC weapons, armor, talismans, spells, consumables, materials, and other items

## Legal Notice

Elden Ring is property of FromSoftware/Bandai Namco. This is an unofficial community tool for local save-file management.

Use responsibly. This project does not endorse online cheating or actions outside the normal bounds of the game.
