#!/bin/bash
cd "$(dirname "$0")"
echo "Starting Newsletter Studio..."
open http://localhost:8765
python3 -m http.server 8765
