"""Generate optimized face mesh data from MediaPipe canonical face model for Three.js."""

import json
import os

OBJ_PATH = r"C:\Users\ASUS\Downloads\Mark-LIV-main\Mark-LIV-main\core\face_model.obj"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "face-model-data.js")

if not os.path.exists(OBJ_PATH):
    print(f"Error: {OBJ_PATH} not found")
    exit(1)

vertices = []
indices = []

with open(OBJ_PATH, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("v "):
            parts = [float(p) for p in line.split()[1:4]]
            # MediaPipe canonical face model OBJ coords:
            # x is horizontal, y is vertical, z is depth
            vertices.append(parts)
        elif line.startswith("f "):
            parts = line.split()[1:4]
            # Convert 1-indexed to 0-indexed
            idx = [int(p.split("/")[0]) - 1 for p in parts]
            indices.extend(idx)

num_vertices = len(vertices)
num_faces = len(indices) // 3
print(f"Loaded {num_vertices} vertices, {num_faces} faces")

# Compute bounding box
xs = [v[0] for v in vertices]
ys = [v[1] for v in vertices]
zs = [v[2] for v in vertices]

min_x, max_x = min(xs), max(xs)
min_y, max_y = min(ys), max(ys)
min_z, max_z = min(zs), max(zs)

center_x = (min_x + max_x) / 2.0
center_y = (min_y + max_y) / 2.0
center_z = (min_z + max_z) / 2.0

scale = max(max_x - min_x, max_y - min_y, max_z - min_z) / 2.0

# Normalize to [-1, 1] range centered around origin
norm_vertices = []
for v in vertices:
    nx = round((v[0] - center_x) / scale, 5)
    ny = round((v[1] - center_y) / scale, 5)
    nz = round((v[2] - center_z) / scale, 5)
    norm_vertices.extend([nx, ny, nz])

# MediaPipe canonical 468 landmarks for facial features:
# Lips outer: [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
# Lips inner: [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]
# Upper lip center: 13, 0
# Lower lip center: 14, 17
# Mouth corners: 61 (left), 291 (right)
# Left eye upper: [159, 160, 161, 158], lower: [145, 144, 153, 154]
# Right eye upper: [386, 385, 387, 388], lower: [374, 373, 380, 381]
# Left eye center / iris: 468 or [33, 133] midpoint
# Right eye center / iris: 473 or [362, 263] midpoint
# Left eyebrow: [70, 63, 105, 66, 107]
# Right eyebrow: [300, 293, 334, 296, 336]
# Chin / Jaw: [152, 175, 199, 200, 18, 17]
# Jawline: [234, 93, 132, 58, 172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288, 361, 454]

# Lower face vertices affected by jaw rotation / mouth opening:
# Vertices with y < center_y in mouth/chin region
jaw_weights = []
for i, v in enumerate(vertices):
    ny = (v[1] - center_y) / scale
    nz = (v[2] - center_z) / scale
    # If in lower half and front facing
    if ny < -0.1:
        # Distance from mouth center
        dist = abs(ny - (-0.45))
        w = max(0.0, min(1.0, 1.0 - (dist / 0.5)))
        jaw_weights.append((i, round(w, 3)))

landmarks = {
    "upperLip": [13, 0, 82, 81, 80, 191, 185, 40, 39, 37, 267, 269, 270, 409, 415, 310, 311, 312],
    "lowerLip": [14, 17, 87, 88, 89, 95, 178, 317, 318, 324, 402, 314, 181, 84],
    "mouthCorners": [61, 291],
    "mouthCenter": 13,
    "chin": [152, 175, 199, 200, 18],
    "leftEyeUpper": [159, 160, 161, 158],
    "leftEyeLower": [145, 144, 153, 154],
    "rightEyeUpper": [386, 385, 387, 388],
    "rightEyeLower": [374, 373, 380, 381],
    "leftEyeCenter": [33, 133],
    "rightEyeCenter": [362, 263],
    "leftEyebrow": [70, 63, 105, 66, 107],
    "rightEyebrow": [300, 293, 334, 296, 336],
    "contour": [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
}

js_content = f"""// MediaPipe Canonical 3D Facial Mesh Data (468 vertices, 898 triangular faces)
// Converted for Three.js Holographic Female AI Assistant HUD
window.SIA_FACE_DATA = {{
  numVertices: {num_vertices},
  numFaces: {num_faces},
  vertices: new Float32Array({json.dumps(norm_vertices)}),
  indices: new Uint16Array({json.dumps(indices)}),
  landmarks: {json.dumps(landmarks)}
}};
"""

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(js_content)

print(f"Generated {OUT_PATH} successfully. Size: {len(js_content)} bytes")
