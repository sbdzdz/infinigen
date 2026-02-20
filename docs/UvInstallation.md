# Installing Infinigen with uv

This guide provides instructions for installing Infinigen using [uv](https://docs.astral.sh/uv/), a fast Python package installer and resolver. This is an alternative to the conda-based installation in the main [Installation.md](Installation.md).

## Why use uv?

- **Faster**: uv is significantly faster than pip and conda for dependency resolution and installation
- **Modern**: Uses standard Python packaging (pyproject.toml) without requiring conda
- **Simpler**: Works with any Python 3.11 installation

## Prerequisites

1. Install uv if you haven't already:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Ensure you have Python 3.11 available on your system

## Platform-Specific System Dependencies

### Mac ARM (M1/M2/M3/...)

```bash
arch -arm64 brew install wget cmake llvm open-mpi libomp glm glew zlib
```

### Mac x86_64 (Intel)

```bash
brew install wget cmake llvm open-mpi libomp glm glew zlib
```

### Linux (Ubuntu/Debian)

```bash
sudo apt-get install wget cmake g++ libgles2-mesa-dev libglew-dev libglfw3-dev libglm-dev zlib1g-dev
```

## Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/princeton-vl/infinigen.git
   cd infinigen
   ```

2. **Create a virtual environment:**
   ```bash
   uv venv --python 3.11
   ```

3. **Pre-compile terrain (Mac ARM only):**

   On Mac ARM, we need to set environment variables for the C++ compiler before installation:
   ```bash
   export CXX=/opt/homebrew/opt/llvm/bin/clang++
   export LDFLAGS="-L/opt/homebrew/opt/libomp/lib"
   export CXXFLAGS="-I/opt/homebrew/opt/libomp/include"

   # Pre-compile terrain components
   bash scripts/install/compile_terrain.sh
   ```

4. **Install scikit-image first (Mac ARM only):**

   Due to build system quirks, install this separately on Mac ARM:
   ```bash
   uv pip install 'scikit-image==0.19.3'
   ```

5. **Install Infinigen:**

   Choose one of the following installation options:

   **Minimal install** (No terrain or OpenGL GT, suitable for Infinigen-Indoors or single-object generation):
   ```bash
   INFINIGEN_MINIMAL_INSTALL=True uv pip install -e .
   ```

   **Full install** (Terrain & OpenGL-GT enabled, needed for Infinigen-Nature HelloWorld):
   ```bash
   # On Mac ARM (with CXX environment variables from step 3 still set):
   uv pip install -e ".[terrain,vis]"

   # On Linux/Mac x86:
   uv pip install -e ".[terrain,vis]"
   ```

   **Installation for simulation assets:**
   ```bash
   uv pip install -e ".[sim]"
   ```

   **Developer install** (includes pytest, ruff, other recommended dev tools):
   ```bash
   uv pip install -e ".[dev,terrain,vis]"
   pre-commit install
   ```

## Verification

Verify the installation:

```bash
uv run python -c "import infinigen; print(f'Infinigen {infinigen.__version__} installed successfully')"
```

## Running Infinigen

You can run Infinigen commands using `uv run`:

```bash
# Example: Generate a scene
uv run python -m infinigen.datagen.manage_jobs --help
```

Or activate the virtual environment first:

```bash
source .venv/bin/activate
python -m infinigen.datagen.manage_jobs --help
```

## Complete Mac ARM Installation Script

Here's a complete installation script for Mac ARM users:

```bash
#!/bin/bash
set -e

# Install system dependencies
arch -arm64 brew install wget cmake llvm open-mpi libomp glm glew zlib

# Clone repository
git clone https://github.com/princeton-vl/infinigen.git
cd infinigen

# Create virtual environment
uv venv --python 3.11

# Set up environment for compilation
export CXX=/opt/homebrew/opt/llvm/bin/clang++
export LDFLAGS="-L/opt/homebrew/opt/libomp/lib"
export CXXFLAGS="-I/opt/homebrew/opt/libomp/include"

# Pre-compile terrain
bash scripts/install/compile_terrain.sh

# Install scikit-image separately
uv pip install 'scikit-image==0.19.3'

# Install Infinigen with terrain and visualization support
uv pip install -e ".[terrain,vis]"

# Verify installation
uv run python -c "import infinigen; print(f'Infinigen {infinigen.__version__} installed successfully')"

echo "Installation complete! Activate with: source .venv/bin/activate"
```

## Troubleshooting

### Issue: "llvmlite" build fails

**Solution**: The installation script pre-installs compatible versions of llvmlite and numba. If you still encounter issues, ensure your Homebrew LLVM is properly installed.

### Issue: Terrain compilation fails with "clang++: No such file or directory"

**Solution**: Make sure the `CXX` environment variable is set before running the installation:
```bash
export CXX=/opt/homebrew/opt/llvm/bin/clang++  # Mac ARM
# or
export CXX=/usr/local/opt/llvm/bin/clang++     # Mac x86
```

### Issue: Git submodules not initialized

**Solution**: The terrain compilation automatically initializes submodules. If needed, manually run:
```bash
git submodule update --init --recursive
```

## Next Steps

Once installed, proceed to:
- [HelloWorld.md](HelloWorld.md) for Infinigen-Nature
- [HelloRoom.md](HelloRoom.md) for Infinigen-Indoors
- [ConfiguringInfinigen.md](ConfiguringInfinigen.md) for configuration options
