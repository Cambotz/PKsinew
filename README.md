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

1. [Quick Setup](#quick-setup)
2. [Install Python 3](#install-python-3)
3. [Install Dependencies](#install-dependencies)
4. [Prepare the Launcher](#prepare-the-launcher)
5. [Add ROMs](#add-roms)
6. [Run the App](#run-the-app)
7. [First-time In-App Setup](#first-time-in-app-setup)
8. [Tips & Notes](#tips--notes)

---

## Quick Setup

Clone the repo:

```bash
git clone https://github.com/Cambotz/PKsinew.git
cd PKsinew
```

> ⚠️ On older macOS/Linux, HTTPS may fail. Use SSH or bypass SSL when cloning.

---

## Install Python 3

| Platform | Instructions |
|----------|--------------|
| **Windows** | [Download Python 3](https://www.python.org/downloads/windows/) |
| **macOS** | [Download Python 3](https://www.python.org/downloads/macos/) |
| **Linux** | See below |

**Linux installation:**

```bash
sudo apt install python3 python3-pip
```

**Verify installation:**

```bash
python3 --version
```

---

## Install Dependencies

```bash
pip3 install pillow numpy pygame requests
```

> **Note:** Pillow replaces PIL. NumPy and Pygame are required for Sinew. requests is used to build the database

---

## Prepare the Launcher

<details>
<summary><b>Windows</b></summary>

Double-click `Sinew.bat` to launch.

</details>

<details>
<summary><b>macOS</b></summary>

1. Make the launcher executable:
   ```bash
   chmod +x Sinew.bat
   ```

2. Right-click `Sinew.bat` → **Get Info** → **Open with:** Terminal → **Change All...**

3. Double-click `Sinew.bat` to run

</details>

<details>
<summary><b>Linux</b></summary>

1. Make the launcher executable:
   ```bash
   chmod +x Sinew.bat
   ```

2. Run from terminal:
   ```bash
   ./Sinew.bat
   ```

   Or create a desktop shortcut pointing to the script.

</details>

---

## Add ROMs

1. Place your legally obtained ROMs in the `roms` folder
2. Supported formats: `.gba`, `.zip`, `.7z`
3. Supported games:
   - Pokémon Ruby
   - Pokémon Sapphire
   - Pokémon Emerald
   - Pokémon FireRed
   - Pokémon LeafGreen

---

## Run the App

```bash
python3 main.py
```

> 💡 **Tip:** Using a controller is strongly recommended for the best experience.

---

## First-time In-App Setup

1. **Map your controller buttons** in Settings
2. **Build the database and wallpapers** via the DB Builder

After this, Sinew is ready to play!

---

## Tips & Notes

- Always run the app from the project folder for proper file paths

- Keep Python packages updated:
  ```bash
  pip3 install --upgrade pillow numpy pygame
  ```

- For older systems, SSH is recommended to avoid GitHub SSL issues

- On macOS/Linux, consider using ed25519 keys for SSH:
  ```bash
  ssh-keygen -t ed25519 -C "your_email@example.com"
  ```

---

## License

MIT License - See [LICENSE](LICENSE) for details.
