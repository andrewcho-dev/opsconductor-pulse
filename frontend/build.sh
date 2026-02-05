#!/usr/bin/env bash
# Build the React frontend for Docker deployment
set -euo pipefail

cd "$(dirname "$0")"
echo "Installing dependencies..."
npm ci
echo "Building React app..."
npm run build
echo "Build complete: dist/"
ls -la dist/
