# Real Classroom Blender Model

This repository keeps the current static Blender classroom model, its generation
script, reference materials, and rendered previews.

## Contents

```text
blender/create_realistic_classroom_preview.py  Blender model generation script
outputs/blender/showcase_classroom_scene.blend Generated Blender scene
outputs/videos/classroom_model_rear_to_front.png Main rear-to-front preview
outputs/videos/classroom_model_lighting_low.png Low-light comparison preview
outputs/videos/classroom_model_lighting_compare.png Side-by-side lighting preview
true_classroom_images/                         Real classroom reference photos
classroom.md                                   Classroom modeling notes
agent.prompt.md                                Modeling prompt/context
天津大学北洋园校区教学楼总图20180529.pdf       Building reference PDF
```

## Run

Run inside the project container:

```bash
cd /workspaces/green
python3 -m py_compile blender/create_realistic_classroom_preview.py
blender --background --python blender/create_realistic_classroom_preview.py
```

The script regenerates the `.blend` file and preview images listed above.
