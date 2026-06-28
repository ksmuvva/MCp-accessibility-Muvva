#!/usr/bin/env bash
# Install the Node engine dependencies (pa11y, Lighthouse, IBM Equal Access).
#
# We skip Puppeteer's Chromium download (the engines reuse the Playwright/system
# Chromium) and skip install scripts so a transitive chromedriver download (used
# only by IBM's optional Selenium path, which we do not use) cannot fail the
# install in locked-down networks.
set -euo pipefail
cd "$(dirname "$0")"

export PUPPETEER_SKIP_DOWNLOAD=1
export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=1

echo "Installing Node accessibility engines..."
npm install --no-audit --no-fund --ignore-scripts
echo "Done. Engines installed in $(pwd)/node_modules"
