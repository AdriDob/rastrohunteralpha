; Rastro Professional Installer for Windows
; Requires NSIS 3.0+ (https://nsis.sourceforge.io)
; Build: makensis installer\install_windows.nsi
;
; Installs to Program Files, registers Windows Service,
; creates shortcuts, adds to Add/Remove Programs.

Unicode True
CRCCheck On

!define PRODUCT_NAME "Rastro"
!define PRODUCT_VERSION "1.6.0"
!define PRODUCT_PUBLISHER "Rastro Labs"
!define PRODUCT_WEB_SITE "https://github.com/AdriDob/rastrohunteralpha"
!define PRODUCT_DIR "$PROGRAMFILES64\${PRODUCT_NAME}"
!define PRODUCT_DATA_DIR "$APPDATA\${PRODUCT_NAME}"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

RequestExecutionLevel admin

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "RastroInstaller.exe"
InstallDir "${PRODUCT_DIR}"
ShowInstDetails show
ShowUnInstDetails show

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "dist\Rastro\*.*"

  ; Create data directory
  CreateDirectory "${PRODUCT_DATA_DIR}"
  CreateDirectory "${PRODUCT_DATA_DIR}\logs"
  CreateDirectory "${PRODUCT_DATA_DIR}\database"

  ; Register Windows Service
  ExecWait '"$INSTDIR\Rastro.exe" --install-service'

  ; Start the service
  ExecWait 'net start Rastro'

  ; Create Start Menu shortcuts
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Rastro Dashboard.lnk" \
    "$INSTDIR\Rastro.exe" "" "$INSTDIR\Rastro.exe" 0
  WriteIniStr "$SMPROGRAMS\${PRODUCT_NAME}\Rastro Dashboard.url" \
    "InternetShortcut" "URL" "http://127.0.0.1:8000"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Rastro Logs.lnk" \
    "$WINDIR\explorer.exe" "${PRODUCT_DATA_DIR}\logs"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall Rastro.lnk" \
    "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0

  ; Desktop shortcut
  CreateShortCut "$DESKTOP\Rastro Dashboard.lnk" \
    "$INSTDIR\Rastro.exe" "" "$INSTDIR\Rastro.exe" 0

  ; Add/Remove Programs entry
  WriteUninstaller "$INSTDIR\uninstall.exe"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\Rastro.exe,0"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoRepair" 1
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "InstallDate" "2026-06-28"

  ; Store install path for service
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "InstallPath" "$INSTDIR"

  ; Open dashboard in browser after install
  ExecShell "open" "http://127.0.0.1:8000"

SectionEnd

Section "Uninstall"
  ; Stop and remove Windows Service
  ExecWait 'net stop Rastro'
  ExecWait '"$INSTDIR\Rastro.exe" --remove-service'

  ; Remove files
  RMDir /r "$INSTDIR"

  ; Remove Start Menu
  RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"
  Delete "$DESKTOP\Rastro Dashboard.lnk"

  ; Remove data directory (keep user data by default)
  ; Uncomment to also remove user data:
  ; RMDir /r "${PRODUCT_DATA_DIR}"

  ; Remove registry
  DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}"
SectionEnd
