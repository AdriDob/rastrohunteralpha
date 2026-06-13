; Rastro Desktop RC1 — NSIS Installer
; Produces: dist\Rastro-Setup-1.0.0.exe
;
; Build: "C:\Program Files\NSIS\makensis.exe" scripts\installer.nsi

Unicode True
ManifestDPIAware true

!define PRODUCT_NAME "Rastro Desktop"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "Rastro AI"
!define PRODUCT_WEB_SITE "https://rastro.ai"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\Rastro.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

SetCompressor lzma
SetCompressorDictSize 32

; ── Paths ────────────────────────────────────────────────────────────
!define BUILD_DIR "..\dist\Rastro"
!define ICON_FILE "..\desktop\build\icons\rastro.ico"
!define OUTPUT_DIR "..\dist"

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "${OUTPUT_DIR}\Rastro-Setup-${PRODUCT_VERSION}.exe"
InstallDir "$PROGRAMFILES64\Rastro Desktop"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
RequestExecutionLevel admin

; ── Interface ────────────────────────────────────────────────────────
!include "MUI2.nsh"
!include "FileFunc.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "${ICON_FILE}"
!define MUI_UNICON "${ICON_FILE}"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP ""
!define MUI_WELCOMEFINISHPAGE_BITMAP ""
!define MUI_WELCOMEPAGE_TITLE "Rastro Desktop ${PRODUCT_VERSION}"
!define MUI_WELCOMEPAGE_TEXT "This wizard will install Rastro Desktop on your computer.$\r$\n$\r$\nRastro is a private investigation desktop application.$\r$\n$\r$\nClick Next to continue."

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_RUN "$INSTDIR\Rastro.exe"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!define MUI_FINISHPAGE_NOREBOOTSUPPORT
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ── Section: Install ─────────────────────────────────────────────────
Section "Install" SecInstall
    SetOutPath "$INSTDIR"
    SetOverwrite on

    ; Copy all files from build output
    File /r "${BUILD_DIR}\*.*"

    ; Copy icon (used for shortcuts)
    File "${ICON_FILE}"

    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\Rastro Desktop"
    CreateShortCut "$SMPROGRAMS\Rastro Desktop\Rastro Desktop.lnk" \
        "$INSTDIR\Rastro.exe" "" "$INSTDIR\rastro.ico" 0 SW_SHOWNORMAL
    CreateShortCut "$SMPROGRAMS\Rastro Desktop\Uninstall.lnk" \
        "$INSTDIR\Uninstall.exe" "" "$INSTDIR\rastro.ico" 0
    CreateShortCut "$DESKTOP\Rastro Desktop.lnk" \
        "$INSTDIR\Rastro.exe" "" "$INSTDIR\rastro.ico" 0 SW_SHOWNORMAL

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Register in Add/Remove Programs
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" \
        "DisplayName" "${PRODUCT_NAME} ${PRODUCT_VERSION}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" \
        "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" \
        "DisplayIcon" "$INSTDIR\rastro.ico"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" \
        "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" \
        "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" \
        "URLInfoAbout" "${PRODUCT_WEB_SITE}"
    WriteRegDWORD ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" \
        "NoModify" 1
    WriteRegDWORD ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" \
        "NoRepair" 1

    ; Add to PATH (optional, for CLI usage)
    WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\Rastro.exe"
    WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "Path" "$INSTDIR"

    ; Estimate installed size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" \
        "EstimatedSize" "$0"
SectionEnd

; ── Section: Uninstall ───────────────────────────────────────────────
Section "Uninstall"
    ; Remove shortcuts
    Delete "$SMPROGRAMS\Rastro Desktop\Rastro Desktop.lnk"
    Delete "$SMPROGRAMS\Rastro Desktop\Uninstall.lnk"
    RMDir "$SMPROGRAMS\Rastro Desktop"
    Delete "$DESKTOP\Rastro Desktop.lnk"

    ; Remove installed files
    RMDir /r "$INSTDIR\*.*"
    RMDir "$INSTDIR"

    ; Remove registry keys
    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
    DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"

    ; Remove user data (prompt user to keep or delete)
    ; User data is in %APPDATA%\Rastro — not removed by default
SectionEnd
