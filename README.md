# LibreVCMI

**LibreVCMI** is a free and open-source (FOSS) asset reimplementation project for the [VCMI](https://github.com/vcmi/vcmi) engine (an open-source recreation of the *Heroes of Might and Magic III* engine).

The goal of this project is to allow VCMI to run out-of-the-box legally and independently without requiring proprietary game data files, by providing a complete set of open-source graphics, sounds, music, videos, and game configs under permissive licenses (primarily [CC0 1.0 Universal](LICENSE)).

---

## Repository Structure

- **`Mods/librevcmi/`** – The ready-to-use VCMI mod package containing strictly 100% libre, handcrafted, and open-source game assets:
  - `GamSelBk.png` – Main menu / scenario selection background (800x600)
  - `librevcmi_logo.png` – LibreVCMI project banner logo
  - `DiBoxBck.png` – Seamless dark oak wood texture (256x256) used for dialog box interiors and letterbox fills on high-resolution widescreen monitors
  - `dialgbox.def` – Modular carved dark walnut wood dialog window frame sprite with player color inlays
- **`tools/`** – Developer utilities to aid in the asset creation and reverse-engineering pipeline:
  - `extract_h3_assets.py` – Tool for locally extracting assets from original game archives (`.lod`, `.snd`, `.vid`) for reference and dimension analysis
  - `setup_librevcmi_stubs.py` – Generator for the developer-only `librevcmi-blackstub` mod, which replaces all missing assets with lightweight labeled black placeholders to easily pinpoint exactly what needs to be created next
  - `generate_librevcmi_dialgbox.py` – Procedural generator for modular `dialgbox.def` window frames and corner ornaments

---

## Installation & Quickstart

1. Install the latest **VCMI engine** (version 1.6+ or built from git).
2. Copy the `Mods/librevcmi` directory into your VCMI user mods directory:
   - **Linux:** `~/.local/share/vcmi/Mods/`
   - **Windows:** `%USERPROFILE%/Documents/My Games/vcmi/Mods/`
   - **macOS:** `~/Library/Application Support/vcmi/Mods/`
3. Launch VCMI and enable the **LibreVCMI** mod in the VCMI Launcher or mod settings.

---

## Project Status & Roadmap

LibreVCMI is currently under active development. The current focus is on providing all core UI backgrounds, dialogue frames, buttons, and cursors required to navigate the menus and basic gameplay seamlessly.

Contributions of original art, UI designs, sound effects, music, and translations are warmly welcome!

---

## License

All original assets and code created for the LibreVCMI project are dedicated to the public domain under the **Creative Commons CC0 1.0 Universal** license (see [LICENSE](LICENSE)).
