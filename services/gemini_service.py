import os
import json
import re
from typing import Dict, Any, List, Optional
import dotenv

dotenv.load_dotenv()

SYSTEM_PROMPT = """
You are a Senior Legal Metrology & Food Safety Compliance Inspector under:
1. Legal Metrology (Packaged Commodities) Rules, 2011 (Ministry of Consumer Affairs, Food & Public Distribution)
2. Food Safety and Standards (Packaging and Labelling / Labelling and Display) Regulations (FSSAI)

Carefully inspect the packaged food / commodity image and the OCR text. Extract every statutory declaration with extreme precision.
Return valid JSON only with exactly these keys:
{
  "product_name": "Generic or common name of the food/commodity (e.g. Potato Chips)",
  "brand": "Brand name (e.g. Parle, ABC Foods)",
  "manufacturer": "Full name and complete address of manufacturer/packer/importer",
  "net_quantity": "Net quantity representation with metric SI unit (e.g. 50 g, 1 kg, 500 ml)",
  "mrp": "Maximum Retail Price with statutory currency indicator (e.g. ₹ 20.00 or Rs. 20.00)",
  "unit_sale_price": "Unit Sale Price per g/ml if indicated (e.g. ₹ 0.40/g) or null",
  "manufacturing_date": "Month and year of manufacture or packaging (e.g. 01/2025)",
  "consumer_care_phone": "Consumer grievance telephone helpline / toll-free number",
  "consumer_care_email": "Customer care / grievance redressal email address",
  "country_of_origin": "Country of origin (e.g. India)",
  "fssai_license": "14-digit FSSAI license or registration number (e.g. 10020011000123) or null if not found",
  "veg_nonveg": "Vegetarian (Green logo) or Non-Vegetarian (Brown logo) or null if missing",
  "ingredients": "Full ingredient list in descending order of weight or volume",
  "nutritional_info": "Complete nutritional values panel (Energy, Protein, Carbohydrates, Total Sugars, Added Sugars, Total Fat, Saturated Fat, Trans Fat, Sodium)",
  "expiry_or_best_before": "Best Before period (e.g. Best before 6 months from packaging) or Expiry / Use By date",
  "batch_number": "Batch number, Lot number, or Code identification",
  "allergen_warning": "Allergen advice statement (e.g. Contains Wheat, Milk, Soy) or null",
  "storage_instructions": "Storage conditions (e.g. Store in a cool and dry place away from sunlight)",
  "all_extracted_text_segments": ["List of all visible text lines/segments detected on the package"]
}

If any statutory declaration is absent from the packaging, set its value to null.
Do NOT hallucinate. Return valid JSON only.
"""

def extract_declarations_regex(raw_text: str, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fallback deterministic extractor if Gemini API key is missing or unavailable."""
    fields = {
        "product_name": "",
        "brand": "",
        "manufacturer": "",
        "net_quantity": "",
        "mrp": "",
        "unit_sale_price": "",
        "manufacturing_date": "",
        "consumer_care_phone": "",
        "consumer_care_email": "",
        "country_of_origin": "India",
        "fssai_license": "",
        "veg_nonveg": "",
        "ingredients": "",
        "nutritional_info": "",
        "expiry_or_best_before": "",
        "batch_number": "",
        "allergen_warning": "",
        "storage_instructions": "",
        "all_extracted_text_segments": []
    }

    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    fields["all_extracted_text_segments"] = lines

    for line in lines:
        # Manufacturer
        if re.search(r"(?:MFR|Manufactured|Mfg\.|Manufacturer|Packer|Packed)\s*(?:by|:|-)?\s*(.+)", line, re.I):
            m = re.search(r"(?:MFR|Manufactured|Mfg\.|Manufacturer|Packer|Packed)\s*(?:by|:|-)?\s*(.+)", line, re.I)
            if m and not fields["manufacturer"]: fields["manufacturer"] = m.group(1).strip()

        # Net Quantity
        if re.search(r"(?:Net\s*(?:Wt|Weight|Quantity|Qty|Vol|Volume))?\s*(?::|-)?\s*([0-9]+(?:\.[0-9]+)?\s*(?:g|kg|ml|l|grams|kilograms|litres|pcs|units|N))\b", line, re.I):
            m = re.search(r"([0-9]+(?:\.[0-9]+)?\s*(?:g|kg|ml|l|grams|kilograms|litres|pcs|units|N))\b", line, re.I)
            if m and not fields["net_quantity"]: fields["net_quantity"] = m.group(1).strip()

        # MRP
        if re.search(r"(?:MRP|Maximum\s*Retail\s*Price)?\s*(?:Rs\.?|₹|:|-)?\s*([0-9]+(?:\.[0-9]{2})?)", line, re.I):
            m = re.search(r"(?:Rs\.?|₹)\s*([0-9]+(?:\.[0-9]{2})?)", line, re.I)
            if m and not fields["mrp"]: fields["mrp"] = "₹ " + m.group(1).strip()

        # USP (Unit Sale Price)
        if re.search(r"(?:Unit\s*Sale\s*Price|USP)\s*(?::|-)?\s*([₹Rs\.\s0-9\/\w]+)", line, re.I):
            m = re.search(r"(?:Unit\s*Sale\s*Price|USP)\s*(?::|-)?\s*([₹Rs\.\s0-9\/\w]+)", line, re.I)
            if m and not fields["unit_sale_price"]: fields["unit_sale_price"] = m.group(1).strip()

        # Manufacturing Date
        if re.search(r"(?:Pkd|Packing|Mfg|Manufactured|Mfd|Date)\s*(?:Date|:|-)?\s*((?:0?[1-9]|1[0-2])[\/\.-](?:20)?[2-9][0-9]|[A-Za-z]{3}\s*(?:20)?[2-9][0-9])", line, re.I):
            m = re.search(r"((?:0?[1-9]|1[0-2])[\/\.-](?:20)?[2-9][0-9]|[A-Za-z]{3}\s*(?:20)?[2-9][0-9])", line, re.I)
            if m and not fields["manufacturing_date"]: fields["manufacturing_date"] = m.group(1).strip()

        # Phone
        if re.search(r"(?:1800[-s]?[0-9]{2,3}[-s]?[0-9]{4}|[0-9]{10})", line):
            m = re.search(r"(?:1800[-s]?[0-9]{2,3}[-s]?[0-9]{4}|[0-9]{10})", line)
            if m and not fields["consumer_care_phone"]: fields["consumer_care_phone"] = m.group(0).strip()

        # Email
        if re.search(r"([a-zA-Z0-9_\.\-]+@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,6})", line):
            m = re.search(r"([a-zA-Z0-9_\.\-]+@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,6})", line)
            if m and not fields["consumer_care_email"]: fields["consumer_care_email"] = m.group(1).strip()

        # Country of Origin
        if re.search(r"(?:Country\s*of\s*Origin|Made\s*in)\s*(?::|-)?\s*(.+)", line, re.I):
            m = re.search(r"(?:Country\s*of\s*Origin|Made\s*in)\s*(?::|-)?\s*(.+)", line, re.I)
            if m: fields["country_of_origin"] = m.group(1).strip()

        # FSSAI License (14 digits)
        if re.search(r"(?:fssai|lic(?:ence|\.|\s*no)?)\s*[:\.-]?\s*([0-9]{14})", line, re.I):
            m = re.search(r"(?:fssai|lic(?:ence|\.|\s*no)?)\s*[:\.-]?\s*([0-9]{14})", line, re.I)
            if m and not fields["fssai_license"]: fields["fssai_license"] = m.group(1).strip()
        elif re.search(r"\b([0-9]{14})\b", line):
            m = re.search(r"\b([0-9]{14})\b", line)
            if m and not fields["fssai_license"]: fields["fssai_license"] = m.group(1).strip()

        # Veg / Non-Veg
        if re.search(r"\b(100%\s*vegetarian|vegetarian|green\s*dot|veg)\b", line, re.I):
            if not fields["veg_nonveg"]: fields["veg_nonveg"] = "Vegetarian"
        elif re.search(r"\b(non-vegetarian|non\s*veg|brown\s*dot)\b", line, re.I):
            if not fields["veg_nonveg"]: fields["veg_nonveg"] = "Non-Vegetarian"

        # Ingredients
        if re.search(r"(?:ingredients?|contains)\s*[:\.-]?\s*(.+)", line, re.I):
            m = re.search(r"(?:ingredients?|contains)\s*[:\.-]?\s*(.+)", line, re.I)
            if m and not fields["ingredients"]: fields["ingredients"] = m.group(1).strip()

        # Expiry or Best Before
        if re.search(r"(?:best\s*before|use\s*by|expiry|exp\s*date)\s*[:\.-]?\s*(.+)", line, re.I):
            m = re.search(r"(?:best\s*before|use\s*by|expiry|exp\s*date)\s*[:\.-]?\s*(.+)", line, re.I)
            if m and not fields["expiry_or_best_before"]: fields["expiry_or_best_before"] = m.group(1).strip()

        # Batch Number
        if re.search(r"(?:batch|lot|b\.?\s*no)\s*[:\.-]?\s*([a-zA-Z0-9\-]+)", line, re.I):
            m = re.search(r"(?:batch|lot|b\.?\s*no)\s*[:\.-]?\s*([a-zA-Z0-9\-]+)", line, re.I)
            if m and not fields["batch_number"]: fields["batch_number"] = m.group(1).strip()

        # Allergen Warning
        if re.search(r"(?:allergen|allergy|contains\s*(?:wheat|milk|nuts|gluten|soy))\s*[:\.-]?\s*(.+)", line, re.I):
            m = re.search(r"(?:allergen|allergy|contains\s*(?:wheat|milk|nuts|gluten|soy))\s*[:\.-]?\s*(.+)", line, re.I)
            if m and not fields["allergen_warning"]: fields["allergen_warning"] = m.group(0).strip()

        # Storage Instructions
        if re.search(r"(?:store\s*in|keep\s*in|store\s*away)\s*(.+)", line, re.I):
            m = re.search(r"(?:store\s*in|keep\s*in|store\s*away)\s*(.+)", line, re.I)
            if m and not fields["storage_instructions"]: fields["storage_instructions"] = m.group(0).strip()

        # Nutrition lines
        if re.search(r"(?:energy|protein|carbohydrate|sugar|fat|sodium)\s*[:\.-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:kcal|g|mg))", line, re.I):
            if not fields["nutritional_info"]:
                fields["nutritional_info"] = line
            else:
                fields["nutritional_info"] += "; " + line

    if lines and not fields["product_name"]:
        fields["product_name"] = lines[0]
        fields["brand"] = lines[0].split()[0] if lines[0].split() else ""

    return fields

def extract_declarations_ai(raw_text: str, detections: List[Dict[str, Any]], image_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Extracts comprehensive Legal Metrology and FSSAI Packaged Food statutory declarations
    using Gemini 3.6 Flash multimodal vision, with deterministic regex fallback.
    Guarantees every extracted text segment is captured and returned in structured JSON.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("No GEMINI_API_KEY found. Utilizing deterministic regex extractor.")
        return extract_declarations_regex(raw_text, detections)

    try:
        from google import genai
        from PIL import Image

        client = genai.Client(api_key=api_key)
        model_name = os.environ.get("GEMINI_MODEL") or "gemini-3.6-flash"

        prompt = f"""
{SYSTEM_PROMPT}

RAW OCR DETECTED TEXT STREAM:
{raw_text}

Analyze the packaging photograph and the raw OCR stream above. Extract every statutory declaration and compile all visible text into the required JSON schema.
"""
        contents = []
        if image_path and os.path.exists(image_path):
            try:
                pil_img = Image.open(image_path)
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                # Optimize transmission size while maintaining high clarity for fine print
                pil_img.thumbnail((1200, 1200))
                contents.append(pil_img)
            except Exception as img_err:
                print(f"Failed to load image for Gemini vision: {img_err}")

        contents.append(prompt)

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
        )

        res_text = response.text.strip()
        # Clean markdown codeblocks
        if "```" in res_text:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", res_text, re.DOTALL)
            if m:
                res_text = m.group(1)
            else:
                res_text = res_text.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(res_text.strip())

        # Ensure all_extracted_text_segments includes OCR detections as well
        ocr_lines = [d["text"] for d in detections if d.get("text")]
        existing_segments = set(parsed.get("all_extracted_text_segments", []))
        for line in ocr_lines:
            if line not in existing_segments:
                parsed.setdefault("all_extracted_text_segments", []).append(line)
                existing_segments.add(line)

        return parsed

    except Exception as e:
        print(f"Gemini API call failed ({e}). Falling back to deterministic regex extraction.")
        return extract_declarations_regex(raw_text, detections)
