"""
YOLOv8-Seg ONNX Inference Wrapper.

Runs a YOLOv8 segmentation model exported to ONNX format via ONNX Runtime.
No PyTorch dependency required — CPU inference only.

Usage:
    from simulator.yolo_inference import YOLOInference

    yolo = YOLOInference("backend/models/best.onnx")
    detections = yolo.predict(image_bgr)
    annotated = yolo.annotate_image(image_bgr, detections)
"""

import os
import numpy as np
from typing import Optional

# Class names matching the training configuration in dataset.yaml
CLASS_NAMES = ["crack", "erosion", "moisture", "discoloration"]


class YOLOInference:
    """
    YOLOv8-seg inference via ONNX Runtime.

    Parameters
    ----------
    model_path : str
        Path to the exported ONNX model file.
    conf_threshold : float
        Minimum confidence for detection filtering.
    iou_threshold : float
        IoU threshold for non-maximum suppression.
    input_size : int
        Expected input image dimension (square).
    class_names : list of str, optional
        Class name list aligned with model output indices.
    """

    def __init__(
        self,
        model_path: str,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        input_size: int = 640,
        class_names: Optional[list] = None,
    ):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self.class_names = class_names or CLASS_NAMES
        self.session = None

        # Lazy-load ONNX Runtime to avoid hard dependency if model is absent
        self._load_model()

    def _load_model(self):
        """Load the ONNX model. Fails gracefully if model file is missing."""
        if not os.path.isfile(self.model_path):
            print(
                f"[YOLOInference] Model not found at {self.model_path}. "
                f"Inference will return empty detections."
            )
            return

        try:
            import onnxruntime as ort

            self.session = ort.InferenceSession(
                self.model_path,
                providers=["CPUExecutionProvider"],
            )
        except ImportError:
            print(
                "[YOLOInference] onnxruntime not installed. "
                "Install with: pip install onnxruntime"
            )
        except Exception as e:
            print(f"[YOLOInference] Failed to load ONNX model: {e}")

    def _preprocess(self, image: np.ndarray) -> tuple:
        """
        Letterbox resize and normalize image for YOLO input.

        Returns
        -------
        blob : np.ndarray
            Preprocessed image tensor (1, 3, H, W) float32.
        ratio : float
            Scale ratio applied.
        pad : tuple
            (pad_w, pad_h) padding added.
        orig_shape : tuple
            Original image (h, w).
        """
        orig_h, orig_w = image.shape[:2]
        ratio = min(
            self.input_size / orig_w, self.input_size / orig_h
        )
        new_w = int(orig_w * ratio)
        new_h = int(orig_h * ratio)

        # Resize using nearest-neighbor (simple, no OpenCV needed for basic)
        # But for quality, use cv2 if available
        try:
            import cv2
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        except ImportError:
            # Fallback: simple resize via numpy (lower quality)
            resized = self._numpy_resize(image, new_w, new_h)

        # Create letterboxed canvas
        canvas = np.full(
            (self.input_size, self.input_size, 3), 114, dtype=np.uint8
        )
        pad_w = (self.input_size - new_w) // 2
        pad_h = (self.input_size - new_h) // 2
        canvas[pad_h : pad_h + new_h, pad_w : pad_w + new_w] = resized

        # HWC -> CHW, BGR -> RGB, normalize to [0, 1]
        blob = canvas[:, :, ::-1].transpose(2, 0, 1).astype(np.float32) / 255.0
        blob = np.expand_dims(blob, axis=0)  # Add batch dim

        return blob, ratio, (pad_w, pad_h), (orig_h, orig_w)

    @staticmethod
    def _numpy_resize(image: np.ndarray, new_w: int, new_h: int) -> np.ndarray:
        """Simple nearest-neighbor resize using numpy (fallback)."""
        orig_h, orig_w = image.shape[:2]
        row_idx = (np.arange(new_h) * orig_h // new_h).astype(int)
        col_idx = (np.arange(new_w) * orig_w // new_w).astype(int)
        return image[np.ix_(row_idx, col_idx)]

    def predict(self, image: np.ndarray) -> list[dict]:
        """
        Run inference on an image.

        Parameters
        ----------
        image : np.ndarray
            Input image in BGR format (H, W, 3), uint8.

        Returns
        -------
        list of dict
            Each dict contains:
                - "class_id" (int): predicted class index
                - "class_name" (str): human-readable class name
                - "confidence" (float): detection confidence
                - "bbox" (list): [x1, y1, x2, y2] in original image coords
                - "area_ratio" (float): bbox area / total image area
                - "mask" (np.ndarray or None): binary segmentation mask
                  at original image resolution (if model provides masks)
        """
        if self.session is None:
            return []

        orig_h, orig_w = image.shape[:2]
        total_area = orig_h * orig_w

        blob, ratio, (pad_w, pad_h), _ = self._preprocess(image)

        # Run ONNX inference
        input_name = self.session.get_inputs()[0].name
        outputs = self.session.run(None, {input_name: blob})

        # YOLOv8-seg produces two outputs:
        #   output0: detection predictions (1, num_det, 4+nc+nm)
        #   output1: prototype masks (1, nm, mh, mw)
        predictions = outputs[0]  # (1, num_dets, features)
        proto_masks = outputs[1] if len(outputs) > 1 else None

        detections = self._postprocess(
            predictions, proto_masks, ratio, pad_w, pad_h,
            orig_h, orig_w, total_area
        )

        return detections

    def _postprocess(
        self, predictions, proto_masks, ratio, pad_w, pad_h,
        orig_h, orig_w, total_area
    ) -> list[dict]:
        """
        Post-process raw ONNX outputs into structured detections.
        Handles both detection-only and segmentation model outputs.
        """
        # predictions shape: (1, num_features, num_candidates) for YOLOv8
        preds = predictions[0]  # Remove batch dim

        # YOLOv8 outputs: (features, candidates) — need to transpose
        if preds.shape[0] < preds.shape[1]:
            preds = preds.T  # -> (candidates, features)

        num_classes = len(self.class_names)

        # Extract components
        boxes = preds[:, :4]  # cx, cy, w, h
        class_scores = preds[:, 4 : 4 + num_classes]
        mask_coeffs = preds[:, 4 + num_classes :] if preds.shape[1] > 4 + num_classes else None

        # Get best class per candidate
        class_ids = np.argmax(class_scores, axis=1)
        confidences = np.max(class_scores, axis=1)

        # Filter by confidence
        mask = confidences > self.conf_threshold
        filtered_boxes = boxes[mask]
        filtered_scores = confidences[mask]
        filtered_classes = class_ids[mask]
        filtered_coeffs = mask_coeffs[mask] if mask_coeffs is not None else None

        if len(filtered_boxes) == 0:
            return []

        # Convert cx, cy, w, h -> x1, y1, x2, y2
        x1 = filtered_boxes[:, 0] - filtered_boxes[:, 2] / 2
        y1 = filtered_boxes[:, 1] - filtered_boxes[:, 3] / 2
        x2 = filtered_boxes[:, 0] + filtered_boxes[:, 2] / 2
        y2 = filtered_boxes[:, 1] + filtered_boxes[:, 3] / 2

        # Remove letterbox padding and rescale to original coords
        x1 = (x1 - pad_w) / ratio
        y1 = (y1 - pad_h) / ratio
        x2 = (x2 - pad_w) / ratio
        y2 = (y2 - pad_h) / ratio

        # Clip to image bounds
        x1 = np.clip(x1, 0, orig_w)
        y1 = np.clip(y1, 0, orig_h)
        x2 = np.clip(x2, 0, orig_w)
        y2 = np.clip(y2, 0, orig_h)

        # NMS
        keep = self._nms(
            np.stack([x1, y1, x2, y2], axis=1),
            filtered_scores,
            self.iou_threshold,
        )

        detections = []
        for idx in keep:
            bx1, by1, bx2, by2 = x1[idx], y1[idx], x2[idx], y2[idx]
            box_area = max(0, (bx2 - bx1)) * max(0, (by2 - by1))

            seg_mask = None
            area_ratio = box_area / total_area

            # Compute segmentation mask if prototypes are available
            if proto_masks is not None and filtered_coeffs is not None:
                seg_mask = self._compute_seg_mask(
                    proto_masks[0], filtered_coeffs[idx],
                    ratio, pad_w, pad_h, orig_h, orig_w
                )
                if seg_mask is not None:
                    # Use mask pixel count for more accurate area ratio
                    area_ratio = float(np.sum(seg_mask)) / total_area

            detections.append({
                "class_id": int(filtered_classes[idx]),
                "class_name": self.class_names[int(filtered_classes[idx])],
                "confidence": float(filtered_scores[idx]),
                "bbox": [float(bx1), float(by1), float(bx2), float(by2)],
                "area_ratio": float(np.clip(area_ratio, 0.0, 1.0)),
                "mask": seg_mask,
            })

        return detections

    def _compute_seg_mask(
        self, protos, coeffs, ratio, pad_w, pad_h, orig_h, orig_w
    ) -> Optional[np.ndarray]:
        """
        Compute binary segmentation mask from prototype masks and coefficients.
        """
        try:
            import cv2
        except ImportError:
            return None

        # protos: (nm, mh, mw), coeffs: (nm,)
        mask = np.einsum("chw,c->hw", protos, coeffs)
        mask = 1 / (1 + np.exp(-mask))  # sigmoid

        # Resize mask to input_size
        mask = cv2.resize(mask, (self.input_size, self.input_size))

        # Remove padding
        mask = mask[pad_h : pad_h + int(orig_h * ratio),
                     pad_w : pad_w + int(orig_w * ratio)]

        # Resize to original image dimensions
        mask = cv2.resize(mask, (orig_w, orig_h))

        # Binarize
        return (mask > 0.5).astype(np.uint8)

    @staticmethod
    def _nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> list:
        """Simple greedy Non-Maximum Suppression."""
        if len(boxes) == 0:
            return []

        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)

        order = scores.argsort()[::-1]
        keep = []

        while len(order) > 0:
            i = order[0]
            keep.append(i)

            if len(order) == 1:
                break

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-8)

            remaining = np.where(iou <= iou_threshold)[0]
            order = order[remaining + 1]

        return keep

    def annotate_image(
        self, image: np.ndarray, detections: list[dict],
        alpha: float = 0.4
    ) -> np.ndarray:
        """
        Draw bounding boxes and semi-transparent segmentation masks
        on the image for Streamlit display.

        Parameters
        ----------
        image : np.ndarray
            Original BGR image.
        detections : list of dict
            Output from self.predict().
        alpha : float
            Mask overlay transparency.

        Returns
        -------
        np.ndarray
            Annotated image (BGR).
        """
        try:
            import cv2
        except ImportError:
            return image

        annotated = image.copy()

        # Color palette per class (BGR)
        colors = {
            "crack": (0, 0, 220),       # Red
            "erosion": (0, 140, 255),    # Orange
            "moisture": (255, 180, 0),   # Cyan-blue
            "discoloration": (0, 200, 200),  # Yellow
        }

        for det in detections:
            cls_name = det["class_name"]
            conf = det["confidence"]
            bbox = det["bbox"]
            mask = det.get("mask")
            color = colors.get(cls_name, (200, 200, 200))

            # Draw bbox
            pt1 = (int(bbox[0]), int(bbox[1]))
            pt2 = (int(bbox[2]), int(bbox[3]))
            cv2.rectangle(annotated, pt1, pt2, color, 2)

            # Label
            label = f"{cls_name} {conf:.2f} ({det['area_ratio']*100:.1f}%)"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(
                annotated,
                (pt1[0], pt1[1] - th - 6),
                (pt1[0] + tw, pt1[1]),
                color, -1,
            )
            cv2.putText(
                annotated, label,
                (pt1[0], pt1[1] - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
            )

            # Overlay segmentation mask
            if mask is not None:
                overlay = annotated.copy()
                overlay[mask == 1] = color
                annotated = cv2.addWeighted(overlay, alpha, annotated, 1 - alpha, 0)

        return annotated


def is_model_available(model_path: str) -> bool:
    """Check whether a trained ONNX model exists at the given path."""
    return os.path.isfile(model_path)
