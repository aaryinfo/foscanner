#!/bin/bash
# Gann Time Cycle — Quick Launcher
cd "$(dirname "$0")"
echo ""
echo "═══════════════════════════════════════════"
echo "  Gann Time Cycle Dashboard — NSE F&O"
echo "═══════════════════════════════════════════"
echo ""
pip install -q yfinance pandas numpy flask 2>/dev/null
python gann_app.py
