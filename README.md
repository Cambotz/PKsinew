Sinew Setup Guide

Welcome to Sinew! Follow this guide to set up the app on Windows, macOS, or Linux.

Table of Contents

Clone the Repository

Install Python 3

Install Dependencies

Prepare the Launcher

Add ROMs

Run the App

First-time In-App Setup

Tips & Notes

1. Clone the Repository

Open your terminal or command prompt:

git clone https://github.com/Cambotz/PKsinew.git
cd PKsinew


⚠️ macOS 10.11 / old Linux users: HTTPS may fail. Use SSH for GitHub or bypass SSL when cloning.

2. Install Python 3

Ensure Python 3 is installed:

Windows: Download Python 3

macOS: Download Python 3

Linux: Use your package manager:

sudo apt install python3 python3-pip


Verify installation:

python3 --version

3. Install Dependencies

Install required Python packages:

pip3 install pillow numpy


Note: Pillow replaces the old PIL library. Numpy is required for internal calculations.

4. Prepare the Launcher
Windows

Double-click sinew.bat to launch.

macOS/Linux

Make the launcher executable:

chmod +x sinew.bat


macOS: Right-click sinew.bat → Always Launch in Terminal
Linux: Ensure it’s executable and run from a terminal or shortcut

5. Add Your ROMs

Move your ethically sourced ROMs into the rom folder inside the project.

Make sure the files are in the correct format required by the app.

6. Run the App

Launch the app:

python3 main.py


Recommended: Use a controller for the best experience.

7. First-time In-App Setup

Map your controller buttons

Build the database and wallpapers

Once complete, the app is ready to play.

8. Tips & Notes

Always run the app from the project folder to ensure correct file paths.

Keep Python packages updated:

pip3 install --upgrade pillow numpy


For older macOS/Linux systems, consider SSH for GitHub to avoid SSL issues.

This README assumes you are running the latest supported version of Python 3 for your system.

💡 Optional Enhancements for Users

Add a .command launcher on macOS for double-click convenience

Keep your ROMs organized in subfolders for easier navigation