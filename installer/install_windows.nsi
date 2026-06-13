; Rastro NSIS Installer for Windows
; Requires NSIS 3.0+ (https://nsis.sourceforge.io)
; Build: makensis install_windows.nsi

Unicode True
CRCCheck On

!define PRODUCT_NAME "Rastro"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "Rastro Labs"
!define PRODUCT_WEB_SITE "https://github.com/AdriDob/rastrohunteralpha"
!define PRODUCT_DIR "$LOCALAPPDATA\${PRODUCT_NAME}"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

RequestExecutionLevel user

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "Rastro_Setup_${PRODUCT_VERSION}.exe"
InstallDir "${PRODUCT_DIR}"
ShowInstDetails show
ShowUnInstDetails show

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "dist\Rastro\*.*"

  ; Create shortcuts
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Rastro.lnk" "$INSTDIR\Rastro.exe" "" "$INSTDIR\Rastro.exe" 0
  CreateShortCut "$DESKTOP\Rastro.lnk" "$INSTDIR\Rastro.exe" "" "$INSTDIR\Rastro.exe" 0

  ; Add/Remove Programs entry
  WriteUninstaller "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegDWORD HKCU "${PRODUCT_UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${PRODUCT_UNINST_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  ; Remove files
  RMDir /r "$INSTDIR"

  ; Remove shortcuts
  RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"
  Delete "$DESKTOP\Rastro.lnk"

  ; Remove registry
  DeleteRegKey HKCU "${PRODUCT_UNINST_KEY}"
SectionEnd
