#!/bin/bash
# Render 5 quick walkthrough videos from the existing bathroom scene

set -e

cd /Users/sebastian/repos/infinigen

if command -v uv >/dev/null 2>&1; then
    PYTHON_CMD=(uv run python)
elif [ -x ".venv/bin/python" ]; then
    PYTHON_CMD=(.venv/bin/python)
else
    echo "ERROR: No project Python found. Install uv or create .venv/bin/python."
    exit 1
fi

SCENE="outputs/indoors/coarse/scene.blend"
PYTHONPATH_VALUE="/Users/sebastian/repos/infinigen:/Users/sebastian/repos/infinigen/.venv/lib/python3.11/site-packages"

echo "=========================================="
echo "Rendering 5 Quick Walkthrough Videos"
echo "=========================================="
echo "Scene: $SCENE"
echo "Python: ${PYTHON_CMD[*]}"
echo "PYTHONPATH: $PYTHONPATH_VALUE"
echo ""

for i in {1..5}; do
    echo "[$i/5] Rendering walkthrough $i..."

    PYTHONPATH="$PYTHONPATH_VALUE" /Applications/Blender.app/Contents/MacOS/Blender \
        "$SCENE" \
        --background \
        --python-use-system-env \
        --python render_walkthrough.py -- --quick 2>&1 | grep -E "(Creating|Rendering|Complete|frames|Mode:|Camera trajectory|RRT animation failed|Falling back)" || true

    # Find the latest quick_test directory
    VIDEO_DIR=$(ls -td outputs/quick_test_* | head -1)

    # Compile video
    ffmpeg -framerate 24 \
        -i "$VIDEO_DIR/frame_%04d.png" \
        -c:v libx264 -pix_fmt yuv420p -crf 23 \
        "$VIDEO_DIR/walkthrough_$i.mp4" \
        -y 2>&1 | grep -E "(frame=|video:)" || true

    # Rename directory
    mv "$VIDEO_DIR" "outputs/bathroom_video_$i"

    echo "  ✓ Video $i: outputs/bathroom_video_$i/walkthrough_$i.mp4"
    echo ""
done

echo "=========================================="
echo "✓ All 5 videos complete!"
echo "=========================================="
echo ""
ls -lh outputs/bathroom_video_*/walkthrough_*.mp4
