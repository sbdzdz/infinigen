#!/bin/bash
# Copyright (C) 2024, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory of this source tree.

# Installation script for Infinigen using uv on Mac ARM (M1/M2/M3/...)

set -e

echo "===== Infinigen Installation with uv (Mac ARM) ====="
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed."
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Error: Homebrew is not installed."
    echo "Install it from: https://brew.sh"
    exit 1
fi

echo "Step 1/6: Installing system dependencies via Homebrew..."
arch -arm64 brew install wget cmake llvm open-mpi libomp glm glew zlib

echo ""
echo "Step 2/6: Creating virtual environment..."
uv venv --python 3.11

echo ""
echo "Step 3/6: Setting up C++ compiler environment..."
export CXX=/opt/homebrew/opt/llvm/bin/clang++
export LDFLAGS="-L/opt/homebrew/opt/libomp/lib"
export CXXFLAGS="-I/opt/homebrew/opt/libomp/include"

echo ""
echo "Step 4/6: Pre-compiling terrain components..."
bash scripts/install/compile_terrain.sh

echo ""
echo "Step 5/6: Installing scikit-image..."
uv pip install 'scikit-image==0.19.3'

echo ""
echo "Step 6/6: Installing Infinigen with terrain and visualization support..."
uv pip install -e ".[terrain,vis]"

echo ""
echo "===== Verifying installation ====="
uv run python -c "import infinigen; print(f'Infinigen {infinigen.__version__} installed successfully!')"

echo ""
echo "Installation complete!"
echo ""
echo "To use Infinigen:"
echo "  1. Activate the environment: source .venv/bin/activate"
echo "  2. Or run with: uv run python -m infinigen.datagen.manage_jobs --help"
echo ""
echo "Next steps:"
echo "  - HelloWorld demo: docs/HelloWorld.md"
echo "  - HelloRoom demo: docs/HelloRoom.md"
