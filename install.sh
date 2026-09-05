#!/usr/bin/env bash
#
# Installs the PyInstaller one-folder build of renamey into /usr/local/opt
# and exposes the launcher on the PATH via a symlink in /usr/local/bin.
#
# Usage:
#   ./install.sh            # build must already exist in dist/renamey
#   ./install.sh uninstall  # remove everything this script installed

set -euo pipefail

APP_NAME="renamey"
BUILD_DIR="dist/${APP_NAME}"
INSTALL_DIR="/usr/local/opt/${APP_NAME}"
BIN_LINK="/usr/local/bin/${APP_NAME}"

# Elevate with sudo only when we can't already write the target locations.
SUDO=""
if [ ! -w "$(dirname "$INSTALL_DIR")" ] || [ ! -w "$(dirname "$BIN_LINK")" ]; then
    SUDO="sudo"
fi

uninstall() {
    echo "Removing ${BIN_LINK}"
    $SUDO rm -f "$BIN_LINK"
    echo "Removing ${INSTALL_DIR}"
    $SUDO rm -rf "$INSTALL_DIR"
    echo "Uninstalled ${APP_NAME}."
}

install() {
    if [ ! -d "$BUILD_DIR" ]; then
        echo "Error: build not found at ${BUILD_DIR}. Run 'make build' first." >&2
        exit 1
    fi

    echo "Installing ${APP_NAME} to ${INSTALL_DIR}"

    $SUDO rm -rf "$INSTALL_DIR"
    $SUDO mkdir -p "$INSTALL_DIR"
    $SUDO cp -R "${BUILD_DIR}/." "$INSTALL_DIR/"

    echo "Linking ${BIN_LINK} -> ${INSTALL_DIR}/${APP_NAME}"
    $SUDO mkdir -p "$(dirname "$BIN_LINK")"
    $SUDO ln -sf "${INSTALL_DIR}/${APP_NAME}" "$BIN_LINK"

    echo "Done. Run '${APP_NAME}' from any directory."
}

case "${1:-install}" in
    uninstall) uninstall ;;
    install)   install ;;
    *) echo "Usage: $0 [install|uninstall]" >&2; exit 1 ;;
esac
