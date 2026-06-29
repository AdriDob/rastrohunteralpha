; ORION — Professional Windows 11 Installer
; Canonical spec: installer\orion.nsi (this file is a symlink for backwards compat)
; Build: makensis installer\orion.nsi
;
; Installs to C:\Program Files\Orion\
; NO Python execution — pure file copy + registry + shortcuts.

!include "orion.nsi"
