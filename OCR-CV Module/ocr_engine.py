import os
import re
import sys

# Ensure UTF-8 output encoding across Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import cv2
import easyocr
import numpy as np

print("[OCR-CV] Initializing EasyOCR Engine (English)...")
# CPU mode for universal compatibility, verbose=False avoids Windows charmap UnicodeEncodeError
reader = easyocr.Reader(["en"], gpu=False, verbose=False)
print("[OCR-CV] Engine Loaded Successfully!")


def check_blur_score(image_cv):
    """
    Measures image sharpness using the Laplacian variance method.
    Scores < 60 generally indicate motion blur or out-of-focus photography.
    """
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    score = cv2.Laplacian(gray, cv2.CV_64F).var()
    return round(float(score), 2)


def preprocess_image_for_ocr(image_cv):
    """
    Applies Computer Vision enhancements to reduce plastic wrapper glare
    and optimize contrast for packaging OCR.
    """
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    # CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    return enhanced


def parse_legal_metrology_declarations(text_lines):
    """
    Analyzes detected OCR lines against Legal Metrology (Packaged Commodities) Rules, 2011.
    Checks for the 7 mandatory declarations required on pre-packaged goods:
    1. Maximum Retail Price (MRP)
    2. Net Quantity / Weight
    3. Date of Manufacture / Packing / Expiry
    4. Consumer Care contact (Email / Phone)
    5. Country of Origin
    6. Manufacturer / Packer Details
    7. Best Before / Expiry declaration
    """
    full_text = " | ".join(text_lines)
    declarations = {
        "mrp": None,
        "net_quantity": None,
        "dates": None,
        "consumer_care": None,
        "country_of_origin": None,
        "manufacturer": None,
        "best_before": None,
    }

    # 1. MRP regex patterns (e.g. MRP Rs. 20, Rs 50, ₹100, Incl. of all taxes)
    mrp_match = re.search(
        r"(?:MRP|M\.R\.P\.?|Rs\.?|₹)\s*[:.\-]?\s*(?:Rs\.?|₹)?\s*([0-9]+(?:\.[0-9]{1,2})?)",
        full_text,
        re.IGNORECASE,
    )
    if mrp_match:
        declarations["mrp"] = {
            "found": True,
            "raw_value": mrp_match.group(0).strip(),
            "amount": mrp_match.group(1).strip(),
            "status": "COMPLIANT",
        }
    else:
        declarations["mrp"] = {"found": False, "status": "MISSING"}

    # 2. Net Quantity regex patterns (e.g. 50g, 100 g, 1 kg, 500 ml, 1 L, 10 N)
    net_qty_match = re.search(
        r"(?:(?:NET\s*(?:WT|WEIGHT|QTY|QUANTITY)?)\s*[:.\-]?\s*)?([0-9]+(?:\.[0-9]+)?\s*(?:g|gm|gms|kg|ml|l|ltr|litres?|units?|pieces?|N))\b",
        full_text,
        re.IGNORECASE,
    )
    if net_qty_match:
        declarations["net_quantity"] = {
            "found": True,
            "raw_value": net_qty_match.group(0).strip(),
            "quantity": net_qty_match.group(1).strip(),
            "status": "COMPLIANT",
        }
    else:
        declarations["net_quantity"] = {"found": False, "status": "MISSING"}

    # 3. Dates (Mfg / Pkd Date)
    date_match = re.search(
        r"(?:MFG|MFD|PKD|PACKED|DATE)\s*[:.\-]?\s*([0-9]{1,2}[/\-\.][0-9]{2,4}|[A-Za-z]{3,9}\s*[0-9]{2,4})",
        full_text,
        re.IGNORECASE,
    )
    if date_match:
        declarations["dates"] = {
            "found": True,
            "raw_value": date_match.group(0).strip(),
            "date": date_match.group(1).strip(),
            "status": "COMPLIANT",
        }
    else:
        declarations["dates"] = {"found": False, "status": "MISSING"}

    # 4. Best Before / Expiry
    bb_match = re.search(
        r"(?:BEST\s*BEFORE|USE\s*BY|EXP\.?\s*DATE|EXPIRY)\s*[:.\-]?\s*([A-Za-z0-9\s/\-\.]+)",
        full_text,
        re.IGNORECASE,
    )
    if bb_match:
        declarations["best_before"] = {
            "found": True,
            "raw_value": bb_match.group(0).strip()[:40],
            "status": "COMPLIANT",
        }
    else:
        declarations["best_before"] = {"found": False, "status": "MISSING"}

    # 5. Consumer Care (Phone / Email)
    care_match = re.search(
        r"([\w\.-]+@[\w\.-]+\.\w+)|(?:(?:CARE|HELPLINE|PHONE|TEL|CONTACT)\s*[:.\-]?\s*(\+?[0-9\-\s]{8,14}))",
        full_text,
        re.IGNORECASE,
    )
    if care_match:
        val = care_match.group(1) or care_match.group(2)
        declarations["consumer_care"] = {
            "found": True,
            "raw_value": val.strip(),
            "status": "COMPLIANT",
        }
    else:
        declarations["consumer_care"] = {"found": False, "status": "MISSING"}

    # 6. Country of Origin
    origin_match = re.search(
        r"(?:COUNTRY\s*OF\s*ORIGIN|MADE\s*IN)\s*[:.\-]?\s*([A-Za-z]+)",
        full_text,
        re.IGNORECASE,
    )
    if origin_match:
        declarations["country_of_origin"] = {
            "found": True,
            "raw_value": origin_match.group(0).strip(),
            "country": origin_match.group(1).strip(),
            "status": "COMPLIANT",
        }
    else:
        declarations["country_of_origin"] = {"found": False, "status": "MISSING"}

    # 7. Manufacturer / Packer Details
    mfr_match = re.search(
        r"(?:MFD\s*BY|MFG\s*BY|PACKED\s*BY|MARKETED\s*BY|MANUFACTURED\s*BY)\s*[:.\-]?\s*([A-Za-z0-9\s,\.\-]+)",
        full_text,
        re.IGNORECASE,
    )
    if mfr_match:
        declarations["manufacturer"] = {
            "found": True,
            "raw_value": mfr_match.group(0).strip()[:50],
            "status": "COMPLIANT",
        }
    else:
        declarations["manufacturer"] = {"found": False, "status": "MISSING"}

    # Calculate overall compliance statistics
    mandatory_keys = ["mrp", "net_quantity", "dates"]
    found_count = sum(1 for k in declarations if declarations[k]["found"])
    total_keys = len(declarations)
    compliance_score = round((found_count / total_keys) * 100, 1)

    mandatory_passed = all(declarations[k]["found"] for k in mandatory_keys)

    return {
        "fields": declarations,
        "total_fields_checked": total_keys,
        "found_fields_count": found_count,
        "compliance_score_pct": compliance_score,
        "critical_mandatory_passed": mandatory_passed,
    }


def draw_visual_annotations(image_cv, detected_lines, compliance_summary):
    """
    Draws clear visual bounding boxes and status labels on detected regions.
    - Green Box: Rule 7 Compliant (Normal font size)
    - Red Box: Rule 7 Non-compliant (Too small font size)
    Adds a top banner showing the Legal Metrology compliance overview.
    """
    annotated = image_cv.copy()
    h_img, w_img, _ = annotated.shape

    # Draw detection bounding boxes
    for line in detected_lines:
        box = line["box"]
        x, y, w, h = box["x"], box["y"], box["w"], box["h"]
        is_normal = line["font_status"] == "NORMAL"
        box_color = (46, 204, 113) if is_normal else (52, 73, 235)  # Green vs Red

        # Draw rectangle
        cv2.rectangle(annotated, (x, y), (x + w, y + h), box_color, 2)

        # Draw label tag above box
        label = f"{line['text'][:20]} [{line['font_status']}]"
        (lbl_w, lbl_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        lbl_y = max(18, y - 5)
        cv2.rectangle(
            annotated,
            (x, lbl_y - lbl_h - 4),
            (x + lbl_w + 6, lbl_y + 2),
            box_color,
            -1,
        )
        cv2.putText(
            annotated,
            label,
            (x + 3, lbl_y - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    # Add header banner
    banner_height = 40
    overlay = annotated.copy()
    cv2.rectangle(overlay, (0, 0), (w_img, banner_height), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.8, annotated, 0.2, 0, annotated)

    status_text = (
        f"Legal Metrology AI | Compliance: {compliance_summary['compliance_score_pct']}% | "
        f"Detections: {len(detected_lines)}"
    )
    cv2.putText(
        annotated,
        status_text,
        (15, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 255, 200),
        2,
        cv2.LINE_AA,
    )

    return annotated


def extract_packaging_info(image_path, save_annotated=True, output_dir=None):
    """
    Main entry point for the Legal Metrology AI Pipeline.
    1. Validates image file and evaluates blur sharpness.
    2. Performs OCR extraction with bounding boxes.
    3. Evaluates Rule 7 font-size proportionality.
    4. Parses mandatory statutory declarations (MRP, Net Qty, Dates, etc.).
    5. Optionally saves an annotated visualization image.
    """
    if not os.path.exists(image_path):
        return {"error": f"Image file not found: {image_path}"}

    img = cv2.imread(image_path)
    if img is None:
        return {"error": "Invalid or corrupt image format"}

    h_img, w_img, _ = img.shape
    blur = check_blur_score(img)
    detected_lines = []
    font_heights = []
    raw_texts = []

    # Run EasyOCR
    results = reader.readtext(image_path)
    for bbox, text, conf in results:
        text = text.strip()
        if conf < 0.25 or not text:
            continue

        raw_texts.append(text)
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        x_min, x_max = int(min(xs)), int(max(xs))
        y_min, y_max = int(min(ys)), int(max(ys))

        box_h = max(1, y_max - y_min)
        box_w = max(1, x_max - x_min)
        font_heights.append(box_h)

        # Rule 7 Font Size Proportion Check (Proportion of package height)
        font_ratio = round((box_h / h_img) * 100, 2)
        font_status = "NORMAL" if font_ratio >= 1.2 else "TOO_SMALL"

        detected_lines.append({
            "text": text,
            "confidence": round(float(conf), 3),
            "box": {"x": x_min, "y": y_min, "w": box_w, "h": box_h},
            "font_height_px": box_h,
            "font_ratio_pct": font_ratio,
            "font_status": font_status,
        })

    avg_font = round(float(np.mean(font_heights)), 1) if font_heights else 0

    # Parse Legal Metrology Declarations
    declaration_report = parse_legal_metrology_declarations(raw_texts)

    # Save visual annotated image if requested
    annotated_image_path = None
    if save_annotated and detected_lines:
        annotated_img = draw_visual_annotations(img, detected_lines, declaration_report)
        target_dir = output_dir or os.path.dirname(image_path) or "."
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        annotated_image_path = os.path.join(target_dir, f"annotated_{base_name}.jpg")
        cv2.imwrite(annotated_image_path, annotated_img)

    return {
        "image_size": {"width": w_img, "height": h_img},
        "blur_score": blur,
        "is_blurry": blur < 60.0,
        "total_detections": len(detected_lines),
        "avg_font_px": avg_font,
        "legal_metrology_compliance": declaration_report,
        "lines": detected_lines,
        "full_text": " | ".join(raw_texts),
        "annotated_image_path": annotated_image_path,
    }


if __name__ == "__main__":
    import json

    test_image = "sample.jpg"
    if not os.path.exists(test_image) and len(sys.argv) > 1:
        test_image = sys.argv[1]

    if os.path.exists(test_image):
        print(f"[OCR-CV] Processing '{test_image}'...")
        results = extract_packaging_info(test_image, save_annotated=True)
        print(json.dumps(results, indent=2))
        print(f"\n[OCR-CV] Annotated visualization saved to: {results.get('annotated_image_path')}")
    else:
        print(f"[OCR-CV] Ready. Usage: python ocr_engine.py <path_to_packaging_image>")
