#!/bin/bash
# Generate walkthrough videos for different room types
# Usage: ./generate_room_walkthroughs.sh [room1 room2 ...] or leave empty for all rooms

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
PYTHONPATH_VALUE="/Users/sebastian/repos/infinigen:/Users/sebastian/repos/infinigen/.venv/lib/python3.11/site-packages"

# Define room types
if [ $# -eq 0 ]; then
    # No arguments - generate all room types
    ROOM_TYPES=("Bathroom" "Bedroom" "Kitchen" "DiningRoom" "LivingRoom")
else
    # Use provided room types
    ROOM_TYPES=("$@")
fi

echo "=========================================="
echo "Room Walkthrough Video Generator"
echo "=========================================="
echo "Generating ${#ROOM_TYPES[@]} room type(s): ${ROOM_TYPES[*]}"
echo "Python: ${PYTHON_CMD[*]}"
echo "PYTHONPATH: $PYTHONPATH_VALUE"
echo ""

for ROOM in "${ROOM_TYPES[@]}"; do
    SEED=$(($(date +%s) % 1000000))  # Keep seed under 1 million to avoid overflow
    OUTPUT_DIR="outputs/${ROOM}_$(date +%Y%m%d_%H%M%S)"

    echo ""
    echo "=== Processing $ROOM ==="
    echo "Seed: $SEED"
    echo "Output: $OUTPUT_DIR"
    echo ""

    # Step 1: Generate scene
    echo "[1/3] Generating $ROOM scene..."
    "${PYTHON_CMD[@]}" -m infinigen_examples.generate_indoors \
        --seed $SEED \
        --task coarse \
        --output_folder "$OUTPUT_DIR/coarse" \
        -g fast_solve.gin singleroom.gin \
        -p compose_indoors.terrain_enabled=False \
           restrict_solving.restrict_parent_rooms=\[\"$ROOM\"\] \
        2>&1 | grep -E "(solve|MAIN|finished)" || true

    if [ ! -f "$OUTPUT_DIR/coarse/scene.blend" ]; then
        echo "  ✗ Scene generation failed for $ROOM, skipping..."
        continue
    fi

    echo "  ✓ Scene generated"

    # Step 2: Render walkthrough
    echo "[2/3] Rendering walkthrough video..."
    PYTHONPATH="$PYTHONPATH_VALUE" /Applications/Blender.app/Contents/MacOS/Blender \
        "$OUTPUT_DIR/coarse/scene.blend" \
        --background \
        --python-use-system-env \
        --python render_walkthrough.py -- --quick \
        2>&1 | grep -E "(Creating|Rendering|Complete|Mode:|Camera trajectory)" || true

    # Step 3: Find and compile video
    echo "[3/3] Compiling video..."
    VIDEO_DIR=$(ls -td outputs/quick_test_* 2>/dev/null | head -1)

    if [ -d "$VIDEO_DIR" ]; then
        ffmpeg -framerate 24 \
            -i "$VIDEO_DIR/frame_%04d.png" \
            -c:v libx264 -pix_fmt yuv420p -crf 23 \
            "$VIDEO_DIR/${ROOM}_walkthrough.mp4" \
            -y 2>&1 | grep -E "(frame=|video:)" || true

        # Move to organized location
        mv "$VIDEO_DIR" "$OUTPUT_DIR/walkthrough"

        echo "  ✓ Video: $OUTPUT_DIR/walkthrough/${ROOM}_walkthrough.mp4"
    else
        echo "  ✗ Video compilation failed"
    fi

    echo "  Done with $ROOM"
done

echo ""
echo "=========================================="
echo "✓ All rooms complete!"
echo "=========================================="
echo ""
echo "Videos created:"
for ROOM in "${ROOM_TYPES[@]}"; do
    VIDEO=$(ls -t outputs/${ROOM}_*/walkthrough/*_walkthrough.mp4 2>/dev/null | head -1)
    if [ -n "$VIDEO" ]; then
        SIZE=$(du -h "$VIDEO" | cut -f1)
        echo "  - $ROOM: $VIDEO ($SIZE)"
    fi
done
