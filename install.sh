#!/bin/bash
echo "============================================"
echo "  QVC One-Click Installer (Mac/Linux)"
echo "============================================"
echo ""
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "Python not found! Please install Python 3.11+"
    echo "  Mac:     brew install python@3.11"
    echo "  Ubuntu:  sudo apt install python3.11"
    exit 1
fi
echo "Python found: "
echo ""
echo "Installing QVC..."
pip3 install qvc-overseer
if [ False -ne 0 ]; then
    echo "Installation failed. Try: pip3 install qvc-overseer --user"
    exit 1
fi
echo ""
echo "============================================"
echo "  QVC installed successfully!"
echo ""
echo "  Quick start:"
echo "  1. cd your-project"
echo "  2. qvc scan ."
echo "  3. qvc fix"
echo ""
echo "  Need help?   qvc guide"
echo "============================================"
