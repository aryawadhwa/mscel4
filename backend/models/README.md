# Trained Vision Models

This directory holds exported ONNX weights for YOLOv8-seg packaging defect detection.

## Expected artifact

| File | Description |
|------|-------------|
| `best.onnx` | Best checkpoint from training, exported via Ultralytics (`model.export(format='onnx')`) |

The file is **not** committed to version control by default. Place your trained model here after running the training pipeline.

## Training & export

From the project root (`mscel4/`):

```bash
pip install ultralytics onnxruntime opencv-python

# Fast iteration (nano)
python backend/training/train_yolov8_seg.py train --model yolov8n-seg --epochs 100 --auto-export

# Paper-quality (medium)
python backend/training/train_yolov8_seg.py train --model yolov8m-seg --epochs 150 --auto-export

# Export an existing checkpoint
python backend/training/train_yolov8_seg.py export --weights runs/segment/train/weights/best.pt
```

Export copies `best.onnx` into this folder automatically.

## Dataset

Training uses `backend/training/dataset.yaml`, which points to `backend/data/combined_dataset/` in YOLOv8-seg layout:

- `images/train`, `images/val`
- `labels/train`, `labels/val`
- Classes: crack, erosion, moisture, discoloration (`nc: 4`)

## Model provenance (fill in after training)

| Field | Value |
|-------|-------|
| Base weights | COCO-pretrained `yolov8n-seg` / `yolov8m-seg` |
| Dataset | Hybrid packaging defect dataset (`combined_dataset`) |
| Train date | _YYYY-MM-DD_ |
| Epochs | _e.g. 100_ |
| Image size | 640 |
| **mAP50 (seg)** | _from `validate` command_ |
| **mAP50-95 (seg)** | _from `validate` command_ |
| Per-class AP50 | crack: _, erosion: _, moisture: _, discoloration: _ |

Record validation metrics:

```bash
python backend/training/train_yolov8_seg.py validate --weights runs/segment/train/weights/best.pt
```

## Runtime

The Streamlit UI and `simulator.yolo_inference.YOLOInference` load `backend/models/best.onnx` via `backend/data/adapter_config.yaml` (`yolo_model_path`). If the file is missing, the app falls back to standard (non-vision) simulation.
