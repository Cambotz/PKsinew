PKsinew v1.3.4

This release focuses on stability, correctness, and quality-of-life improvements. 
Several edge-case bugs have been resolved, and internal systems have been refined for more reliable behavior.

Improvements

Resolved additional hardcoded path issues (thanks Jeodc)
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

Thanks to @Jeod for the extensive restructuring work in this release.

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