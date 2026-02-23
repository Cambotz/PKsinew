# PKsinew

**PKsinew** is a companion app/frontend launcher for **Gen 3 Pokémon games** that lets you **track your progress across all 5 GBA games**.

It allows you to:

- Access Sinew **default start+select**
- Gain **achievements and rewards**
- Handle **mass storage & transferring Pokémon between games**
- Access **mythical rewards**
- Explore **re-imagined abandoned features** from the original games
- Export **save data to readable text file** for other projects

PKsinew supports **Windows, macOS, and Linux**, and works best with a **controller** for seamless gameplay tracking.

**Devlog / Updates:** [Sinew Devlog](https://pksinew.hashnode.dev/pksinew-devlog-index-start-here)

**Discord:** [Sinew Discord](https://discord.gg/t28tmQsyuq)

---

## Table of Contents

1. [How to Use](#how-to-use)
   - [Add ROMs](#add-roms)
   - [First-time In-App Setup](#first-time-in-app-setup)
   - [Tips & Notes](#tips--notes)
2. [How to Build ](#building)
   - [Install Python 3](#install-python-3)
   - [Install Dependencies](#install-dependencies)
   - [Build Executable](#build-executable)
   - [Dev Environment](#dev-environment)
3. [Troubleshooting](#troubleshooting)

---

## How to Use

If you downloaded a release, you do **not** need Python or any dependencies. Just follow these steps:

### Add ROMs

1. Place your legally obtained ROMs in the `roms` folder.

- Supported formats: `.gba`, `.zip`, `.7z`
- Supported games:
  - Pokémon Ruby
  - Pokémon Sapphire
  - Pokémon Emerald
  - Pokémon FireRed
  - Pokémon LeafGreen

---

### First-time In-App Setup

1. **Map your controller buttons** in Settings
2. Point each game slot to its ROM file
3. Start playing — achievements and tracking begin automatically

---

### Tips & Notes

- Save files are stored in the `saves/` folder — back these up regularly
- Logs are written to `sinew.log` in the root folder — include this if reporting a bug
- Controller is highly recommended but keyboard works too

---

## Building

If you want to build PKsinew yourself, follow these steps:

### Install Python 3

| Platform    | Instructions                                                      |
| ----------- | ----------------------------------------------------------------- |
| **Windows** | [Download Python 3.12](https://www.python.org/downloads/windows/) |
| **macOS**   | [Download Python 3](https://www.python.org/downloads/macos/)      |
| **Linux**   | See below                                                         |

#### Windows — Important Installation Steps

1. Download **Python 3.12** from the link above (3.12 is recommended for best compatibility)
2. Run the installer
3. **On the first screen, check the box that says "Add Python to PATH"** — this is critical. If you skip this, commands won't work
4. Click **Install Now** and let it finish
5. Open **PowerShell** (search for it in the Start menu) and verify it worked:

```powershell
python --version
```

You should see something like `Python 3.12.x`. If you get an error, you likely missed the PATH checkbox — re-run the installer and check it.

#### macOS

[Download Python 3](https://www.python.org/downloads/macos/) and follow the standard installer.

**Verify installation:**

```bash
python3 --version
```

#### Linux

```bash
sudo apt install python3 python3-pip
```

**Verify installation:**

```bash
python3 --version
```

### Install Dependencies

All commands from this point on need to be run from **inside the PKsinew folder**.

With your terminal open in the PKsinew folder, run:

**Windows (PowerShell):**

```powershell
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
pip3 install -r requirements.txt
```

If you get a permissions error on macOS/Linux, try:

```bash
pip3 install --user -r requirements.txt
```

This will install all required packages (Pillow, NumPy, Pygame, requests, etc.) automatically.

### Build Executable

1. Run the build command from the project root:
   `pyinstaller --clean PKsinew.spec`
2. The built app will appear in the `dist/` folder.

---

### Dev Environment

You can of course run PKsinew from the unpacked `src` folder (e.g. testing changes and other development things), just `cd src` and run `python3 main.py`. PKsinew is configured to know when it's being run in dev mode and should find all resource folders automatically.

## Troubleshooting

**"python is not recognized" error on Windows**

> You missed the "Add Python to PATH" checkbox during installation. Re-run the Python installer, choose "Modify", and enable the PATH option. Or uninstall and reinstall with the checkbox checked.

**"pip is not recognized" on Windows**

> Same cause as above — Python isn't on your PATH. Re-run the installer with the PATH option enabled.

**Black screen / app won't start**

> Make sure all dependencies are installed. See above for running `pip install -r requirements.txt`.

**Game not detected**

> Make sure your ROM filename contains the game name (e.g. `Pokemon Ruby.gba`). Check the `roms/` folder and ensure the file extension is supported.

**Linux: No module named 'pygame.font' / 'pygame.mixer'**

> Try to install pygame through your package manager, and retrying from [Build Executable](#build-executable). This may be called "python3-pygame" or "python-pygame", depending on your distro.