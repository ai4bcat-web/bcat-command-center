#!/bin/bash
# start.sh — Build and start the BCAT Node/Express API server
# Called by Replit on every deploy/run.

set -e

API_DIR="$(dirname "$0")/../artifacts/api-server"

echo "=== BCAT API Server — Build + Start ==="
echo "API dir: $API_DIR"

# Install dependencies if node_modules is missing or package.json changed
if [ ! -d "$API_DIR/node_modules" ]; then
  echo "Installing npm dependencies..."
  cd "$API_DIR" && npm install --include=dev
  cd - > /dev/null
fi

# Build TypeScript → JavaScript
echo "Building TypeScript..."
cd "$API_DIR" && npm run build
cd - > /dev/null

# Export CSV_DATA_DIR to the project root (where the CSV files live)
export CSV_DATA_DIR="$(pwd)"
echo "CSV_DATA_DIR=$CSV_DATA_DIR"

# Start the compiled server
echo "Starting server..."
node "$API_DIR/dist/index.js"
