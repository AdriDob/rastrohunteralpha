.PHONY: help install-windows build-android build-desktop clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install-windows: ## Build Windows portable folder + zip (one-command installer)
	python scripts/install_windows.py

install-windows-full: ## Build Windows portable + NSIS installer
	python scripts/install_windows.py --installer

build-android: ## Build Android debug APK
	python scripts/build_android.py

build-android-release: ## Build Android release APK
	python scripts/build_android.py --release

build-android-clean: ## Clean and rebuild Android debug APK
	python scripts/build_android.py --clean

build-desktop: ## Build desktop bundle via PyInstaller (current OS)
	python desktop/build/build_desktop.py --onedir

build-desktop-onefile: ## Build desktop single-file binary
	python desktop/build/build_desktop.py --onefile

clean: ## Remove build artifacts
	rm -rf dist/
	rm -rf desktop/build/build/
	rm -rf desktop/build/dist/
	rm -rf desktop/build/*.spec
