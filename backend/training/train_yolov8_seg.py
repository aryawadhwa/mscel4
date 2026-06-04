"""
YOLOv8-Seg Training Script for Packaging Defect Detection.

This script provides a complete training pipeline for the segmentation model
used by the Vision Adapter. It is designed to be run on a machine with GPU
access (Colab, local CUDA, etc.) — NOT inside the IDE.

Usage:
    # Install ultralytics
    pip install ultralytics

    # Train (from project root)
    python backend/training/train_yolov8_seg.py --epochs 100 --batch 16 --model yolov8n-seg

    # Paper-quality model
    python backend/training/train_yolov8_seg.py --model yolov8m-seg --epochs 150

    # Export to ONNX after training
    python backend/training/train_yolov8_seg.py --export-only --weights runs/segment/train/weights/best.pt
"""

import argparse
import os
import sys


def train(args):
    """Run YOLOv8-seg training."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    # Resolve dataset config path
    dataset_yaml = os.path.join(os.path.dirname(__file__), "dataset.yaml")
    if not os.path.isfile(dataset_yaml):
        print(f"ERROR: Dataset config not found at {dataset_yaml}")
        sys.exit(1)

    print(f"Training Configuration:")
    print(f"  Model:     {args.model}")
    print(f"  Epochs:    {args.epochs}")
    print(f"  Batch:     {args.batch}")
    print(f"  Image Size: {args.imgsz}")
    print(f"  Dataset:   {dataset_yaml}")
    print(f"  Device:    {args.device}")
    print()

    # Load pretrained model (transfer learning from COCO)
    model = YOLO(f"{args.model}.pt")

    # Train with specified hyperparameters
    results = model.train(
        data=dataset_yaml,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        project=args.project,
        name=args.name,
        patience=args.patience,
        # Augmentation settings tuned for defect detection
        hsv_h=0.015,        # Hue augmentation (subtle for defect colors)
        hsv_s=0.5,          # Saturation augmentation
        hsv_v=0.3,          # Value augmentation
        degrees=15.0,       # Rotation (packaging can be oriented differently)
        translate=0.1,      # Translation
        scale=0.3,          # Scale variation
        flipud=0.3,         # Vertical flip (packaging symmetry)
        fliplr=0.5,         # Horizontal flip
        mosaic=0.8,         # Mosaic augmentation
        mixup=0.1,          # MixUp augmentation (light)
        copy_paste=0.2,     # Copy-paste augmentation for rare classes
        # Training parameters
        lr0=0.01,           # Initial learning rate
        lrf=0.01,           # Final learning rate factor
        warmup_epochs=3.0,  # Warmup epochs
        weight_decay=0.0005,
        # Logging
        verbose=True,
        save=True,
        save_period=10,     # Save checkpoint every 10 epochs
    )

    print("\nTraining complete!")
    print(f"Best weights saved at: {args.project}/{args.name}/weights/best.pt")

    # Auto-export to ONNX if requested
    if args.auto_export:
        export_model(f"{args.project}/{args.name}/weights/best.pt", args.imgsz)

    return results


def export_model(weights_path: str, imgsz: int = 640):
    """Export trained model to ONNX format for CPU inference."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics not installed.")
        sys.exit(1)

    if not os.path.isfile(weights_path):
        print(f"ERROR: Weights file not found at {weights_path}")
        sys.exit(1)

    print(f"\nExporting {weights_path} to ONNX...")
    model = YOLO(weights_path)
    export_path = model.export(
        format="onnx",
        imgsz=imgsz,
        simplify=True,
        dynamic=False,
        opset=12,
    )

    # Copy to the expected model location
    target_path = os.path.join(
        os.path.dirname(__file__), "..", "models", "best.onnx"
    )
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    import shutil
    shutil.copy2(export_path, target_path)
    print(f"ONNX model saved to: {target_path}")
    print("The Vision Adapter will now use this model for inference.")


def validate(args):
    """Run validation on the trained model."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics not installed.")
        sys.exit(1)

    model = YOLO(args.weights)
    dataset_yaml = os.path.join(os.path.dirname(__file__), "dataset.yaml")

    results = model.val(
        data=dataset_yaml,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        verbose=True,
    )

    print("\nValidation Results:")
    print(f"  mAP50:    {results.seg.map50:.4f}")
    print(f"  mAP50-95: {results.seg.map:.4f}")

    # Per-class results
    class_names = ["crack", "erosion", "moisture", "discoloration"]
    for i, name in enumerate(class_names):
        if i < len(results.seg.ap50):
            print(f"  {name}: AP50={results.seg.ap50[i]:.4f}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="YOLOv8-Seg Training for Packaging Defect Detection"
    )

    # Training hyperparameters (flat CLI — spec: --epochs 100 --batch 16 --model yolov8n-seg)
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n-seg",
        choices=["yolov8n-seg", "yolov8s-seg", "yolov8m-seg", "yolov8l-seg", "yolov8x-seg"],
        help="YOLOv8 model variant (default: nano for fast iteration)",
    )
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument(
        "--device", type=str, default="0", help="Device: '0' for GPU 0, 'cpu' for CPU"
    )
    parser.add_argument("--project", type=str, default="runs/segment")
    parser.add_argument("--name", type=str, default="train")
    parser.add_argument("--patience", type=int, default=20, help="Early stopping patience")
    parser.add_argument(
        "--auto-export",
        action="store_true",
        help="Auto-export to ONNX after training",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Export existing weights to ONNX (requires --weights)",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default=None,
        help="Path to trained .pt weights (for --export-only or validation)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run validation on existing weights (requires --weights)",
    )

    args = parser.parse_args()

    if args.export_only:
        if not args.weights:
            print("ERROR: --export-only requires --weights PATH")
            sys.exit(1)
        export_model(args.weights, args.imgsz)
    elif args.validate_only:
        if not args.weights:
            print("ERROR: --validate-only requires --weights PATH")
            sys.exit(1)
        validate(args)
    else:
        if not args.auto_export:
            args.auto_export = True
        train(args)


if __name__ == "__main__":
    main()
