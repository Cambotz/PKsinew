PKsinew v1.3.7

-External Emulator (Experimental), Major Refactor & Save Improvements

⚠️ Important: Save backups are now stored in a separate folder. You must manually move your existing backup files — failure to do so will result in the wrong save files being read.

Code Refactor (by @JeodC)
-Massive codebase refactor and structural cleanup
-Improved modularity and long-term maintainability

External Emulator & Handheld (Experimental, by @JeodC)
-External emulator launch and return to Sinew
-Added dimming support for Sinew on dual-screen devices
-Achievement support when using an external emulator

(external support will be available as more providers are added. currently rocknix but desktop is in the works also)

NEW
-CFW detection
-Support for .zip ROM files
-Support for all save types
-ROM priority system

Improvements
=Save file backups now save to /saves/backups (MUST BE MOVED MANUALY FOR THIS UPDATE)
-Save cache reloading
-Save data now refreshes when entering Trainer Info, Pokédex, and PC Box
-External ROM filtering and detection reliability
-External save handling improvements
-Rocknix provider savefile detection
-More Controller stability improvements

Fixes
-Audio crash when more than 2 channels are present


=================================================================

PKsinew v1.3.6 

NEW:
- Groundwork for external emulator and provider support by (@JeodC)
- Header-based save detection
- SHA-1 ROM detection
- Pause/Menu keyboard binding
- Dev mode toggle for external_emulator.py

Improvements:
- Initial load optimisation
- Controller auto-detection reliability
- Pause/Menu combo no longer requires holding the buttons

Fixes:
- DualSense D-Pad handling
- mGBA audio initialisation fix

Technical:
- Hash database for ROM detection built by (@Fraudbatman)
- Consistent shebangs/docstrings applied across modules and general codebase cleanups by (@JeodC)

===================================================================

PKsinew v1.3.5

New:
- Unified Input tab (Controller + Keyboard merged)
- Added mGBA settings tab
- Fast-forward toggle and speed slider (2x–10x)
- Mute toggle in mGBA settings
- Volume slider added to General settings
- Added audio buffer & queue depth controls
- Automatic handheld detection and fullscreen optimization
- Header-based ROM version detection (thanks to @FraudBatman and @JeodC for the inspiration)
- Added loading screen when returning from emulator

Improvements:
- Improved controller auto-detection
- Improved emulator settings synchronization
- Major path cleanup and config centralization (thanks @JeodC )
- Faster startup and optimized achievement checks

Fixes:
- Fixed Emerald save file detection (thanks @FraudBatman )
- Fixed auto-detected controller configs not passing to emulator(requires testing)
- Fixed keyboard becoming unresponsive after emulator exit
- Fixed display surface crash on return to menu
- Fixed save data bleeding between games
- Fixed reward generation and event ticket storage paths

======================================================================

PKsinew v1.3.4

This release focuses on stability, correctness, and quality-of-life improvements. 
Several edge-case bugs have been resolved, and internal systems have been refined for more reliable behavior.

Improvements

Resolved additional hardcoded path issues (thanks @Jeodc)
Improved achievement checking logic (now triggered on return to Sinew only)
Updated Pokémon sprite rendering in PC Box info panel
Added emulator speed slider and toggle

Bug fixes

Corrected incorrect game achievement checks
Fixed cross-save data appearing in Pokédex, Trainer Card, and PC Box
Prevented moving Pokémon to games without valid save files
Fixed nickname/species name handling issues 

======================================================================
PKsinew v1.3.3

Improvements

Codebase Restructure (PyInstaller Support)

Major internal cleanup and refactor.
Reorganized project structure to properly support PyInstaller packaging.
Improved build reliability for distributed releases.
Establishes a stronger foundation for Windows and Linux binary support.

Thanks to @Jeodc for the extensive restructuring work in this release.

Bug Fixes

Fixed an issue where transferring Pokémon before obtaining the Pokédex could cause errors.

Notes

This release primarily focuses on internal improvements and build stability.
No gameplay changes were introduced beyond the transfer fix.

======================================================================
PKsinew 1.3.2 – Stability & Controller Fixes

Sinew 1.3.2 focuses on resolving input-related issues and improving controller compatibility.

Fixes

Fixed an issue where keyboard inputs could not be properly bound
Fixed a crash caused by using the “Swap A and B” option

Improvements

Added SDL_GameControllerDB to improve controller detection and compatibility across more devices

=======================================================================

PKsinew 1.3.0 – Input & Stability Update
New Features

Added Japanese character support
(Thanks to Randomdice101 on Discord for assistance and testing)

Pokémon Nature now displays correctly in the summary screen
(Thanks to Randomdice101)

Added a footer hint on the main screen to clarify user actions

Implemented keyboard binding configuration screens for:

Sinew controls

Emulator controls

Added controller auto-detection for most mainstream controllers
(Additional testing welcome, as not all controllers are available for verification)

Added support for multiple D-Pad and thumbstick input protocols

Fixes

Fixed Pokémon OT/ID not displaying correctly in the summary screen

Fixed Littleroot Town displaying as “Unknown”
(With help from Randomdice101)

Fixed an issue where spaces in Pokémon nicknames caused names to truncate

Fixed audio stuttering during extended play sessions

Fixed badge detection for Japanese Emerald
(Thanks to Randomdice101)

Performance Improvements

Bypassed the mGBA scaler to improve performance

Removed redundant development and testing code