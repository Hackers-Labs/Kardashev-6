"""
Legal Metrology (Packaged Commodities) Rules, 2011 & FSSAI Packaged Food Labelling Regulations
Evaluates extracted declarations against statutory requirements for packaged food commodities.
Produces a strict 3-state compliance verdict:
- COMPLIANT
- POTENTIAL_NON_COMPLIANCE
- REVIEW_REQUIRED
"""

import re
from typing import Dict, Any, List, Tuple

def evaluate_declarations(declarations: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates statutory package declarations against:
    1. Legal Metrology (Packaged Commodities) Rules, 2011 (DoCA)
    2. Food Safety & Standards (Packaging and Labelling / Labelling & Display) Regulations (FSSAI)
    """

    def get_val(key: str) -> str:
        v = declarations.get(key, "")
        if v is None:
            return ""
        if isinstance(v, dict):
            return str(v.get("value") or "").strip()
        if isinstance(v, list):
            return ", ".join(str(item) for item in v if item).strip()
        return str(v or "").strip()

    # Legal Metrology declarations
    mfr = get_val("manufacturer") or get_val("packer") or get_val("importer")
    prod_name = get_val("product_name")
    net_qty = get_val("net_quantity")
    mrp = get_val("mrp")
    usp = get_val("unit_sale_price")
    mfd_date = get_val("manufacturing_date") or get_val("packing_date")
    care_phone = get_val("consumer_care_phone")
    care_email = get_val("consumer_care_email")
    country = get_val("country_of_origin")

    # Packaged Food statutory declarations
    fssai = get_val("fssai_license")
    veg_nonveg = get_val("veg_nonveg")
    ingredients = get_val("ingredients")
    nutrition = get_val("nutritional_info")
    expiry = get_val("expiry_or_best_before")
    batch = get_val("batch_number")
    allergen = get_val("allergen_warning")
    storage = get_val("storage_instructions")

    rules_evaluation = [
        # =====================================================================
        # PART A: LEGAL METROLOGY (PACKAGED COMMODITIES) RULES, 2011
        # =====================================================================
        {
            "category": "Legal Metrology (Rules 2011)",
            "rule_id": "RULE_6_1_A",
            "field": "Manufacturer Details",
            "rule_name": "Rule 6(1)(a) - Manufacturer / Packer / Importer Identity & Complete Physical Address",
            "extracted_value": mfr,
            "pass": len(mfr) >= 8 and any(c.isalpha() for c in mfr),
            "status": "Verified" if (len(mfr) >= 8 and any(c.isalpha() for c in mfr)) else "Missing",
            "severity": "Critical",
            "penalty": 25000.00,
            "message": "Complete manufacturer/packer identity and address declared." if len(mfr) >= 8 else "Missing or incomplete manufacturer/packer identity or address on packaging."
        },
        {
            "category": "Legal Metrology (Rules 2011)",
            "rule_id": "RULE_6_1_B",
            "field": "Product Name",
            "rule_name": "Rule 6(1)(b) - Common or Generic Commodity Name on Principal Display Panel",
            "extracted_value": prod_name,
            "pass": len(prod_name) >= 2,
            "status": "Verified" if len(prod_name) >= 2 else "Missing",
            "severity": "Medium",
            "penalty": 10000.00,
            "message": "Generic commodity name clearly specified." if len(prod_name) >= 2 else "Missing common/generic product name on principal display panel."
        },
        {
            "category": "Legal Metrology (Rules 2011)",
            "rule_id": "RULE_6_1_C",
            "field": "Net Quantity",
            "rule_name": "Rule 6(1)(c) - Net Quantity in Standard Metric SI Units (g, kg, ml, l)",
            "extracted_value": net_qty,
            "pass": bool(re.search(r"[0-9]+(?:\.[0-9]+)?\s*(?:g|kg|ml|l|grams|kilograms|litres|pcs|units|N)\b", net_qty, re.IGNORECASE)),
            "status": "Verified" if bool(re.search(r"[0-9]+(?:\.[0-9]+)?\s*(?:g|kg|ml|l|grams|kilograms|litres|pcs|units|N)\b", net_qty, re.IGNORECASE)) else "Missing",
            "severity": "Critical",
            "penalty": 25000.00,
            "message": "Standard metric SI unit net quantity declared." if bool(re.search(r"[0-9]+(?:\.[0-9]+)?\s*(?:g|kg|ml|l|grams|kilograms|litres|pcs|units|N)\b", net_qty, re.IGNORECASE)) else "Non-standard or missing net quantity representation."
        },
        {
            "category": "Legal Metrology (Rules 2011)",
            "rule_id": "RULE_6_1_E",
            "field": "Maximum Retail Price (MRP)",
            "rule_name": "Rule 6(1)(e) - Maximum Retail Price (MRP Inclusive of All Taxes)",
            "extracted_value": mrp,
            "pass": bool(re.search(r"(?:₹|Rs\.?)\s*[0-9]+(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?", mrp)),
            "status": "Verified" if bool(re.search(r"(?:₹|Rs\.?)\s*[0-9]+(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?", mrp)) else "Missing",
            "severity": "Critical",
            "penalty": 25000.00,
            "message": "Maximum Retail Price declared with statutory currency indicator." if bool(re.search(r"(?:₹|Rs\.?)\s*[0-9]+(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?", mrp)) else "Missing or illegible Maximum Retail Price (MRP) declaration."
        },
        {
            "category": "Legal Metrology (Rules 2011)",
            "rule_id": "RULE_6_1_D",
            "field": "Manufacturing / Packing Date",
            "rule_name": "Rule 6(1)(d) - Month & Year of Manufacture / Packing / Import",
            "extracted_value": mfd_date,
            "pass": bool(re.search(r"(?:0?[1-9]|1[0-2])[\/\.-](?:20)?[2-9][0-9]|[A-Za-z]{3}\s*(?:20)?[2-9][0-9]", mfd_date)),
            "status": "Verified" if bool(re.search(r"(?:0?[1-9]|1[0-2])[\/\.-](?:20)?[2-9][0-9]|[A-Za-z]{3}\s*(?:20)?[2-9][0-9]", mfd_date)) else "Missing",
            "severity": "Medium",
            "penalty": 10000.00,
            "message": "Month and year of manufacture/pre-packing clearly indicated." if bool(re.search(r"(?:0?[1-9]|1[0-2])[\/\.-](?:20)?[2-9][0-9]|[A-Za-z]{3}\s*(?:20)?[2-9][0-9]", mfd_date)) else "Missing or invalid manufacturing / packaging date format."
        },
        {
            "category": "Legal Metrology (Rules 2011)",
            "rule_id": "RULE_6_2",
            "field": "Consumer Grievance Care Details",
            "rule_name": "Rule 6(2) - Consumer Care Helpline Toll-Free Phone / Email Redressal",
            "extracted_value": f"Phone: {care_phone or 'N/A'} | Email: {care_email or 'N/A'}",
            "pass": len(care_phone) >= 5 or len(care_email) >= 5,
            "status": "Verified" if (len(care_phone) >= 5 or len(care_email) >= 5) else "Missing",
            "severity": "High",
            "penalty": 15000.00,
            "message": "Consumer grievance helpline cell contact verified." if (len(care_phone) >= 5 or len(care_email) >= 5) else "Missing consumer grievance cell helpline number or email on packaging."
        },
        {
            "category": "Legal Metrology (Rules 2011)",
            "rule_id": "RULE_6_1_F",
            "field": "Country of Origin",
            "rule_name": "Rule 6(1)(f) - Country of Origin Declaration",
            "extracted_value": country,
            "pass": len(country) >= 2,
            "status": "Verified" if len(country) >= 2 else "Missing",
            "severity": "Low",
            "penalty": 5000.00,
            "message": "Country of origin declaration clearly stated." if len(country) >= 2 else "Missing country of origin declaration on retail commodity."
        },
        {
            "category": "Legal Metrology (Rules 2011)",
            "rule_id": "RULE_6_11",
            "field": "Unit Sale Price (USP)",
            "rule_name": "Rule 6(11) - Mandatory Unit Sale Price per g/ml for Consumers",
            "extracted_value": usp or "Not declared separately",
            "pass": len(usp) >= 2,
            "status": "Verified" if len(usp) >= 2 else "Review Required",
            "severity": "Low",
            "penalty": 5000.00,
            "message": "Unit Sale Price (USP) declared." if len(usp) >= 2 else "Unit Sale Price not explicitly stated (mandatory if package > standard unit)."
        },

        # =====================================================================
        # PART B: PACKAGED FOOD REGULATIONS & FSSAI STATUTORY STANDARDS
        # =====================================================================
        {
            "category": "Packaged Food Regulations (FSSAI)",
            "rule_id": "FOOD_RULE_FSSAI",
            "field": "FSSAI License / Registration",
            "rule_name": "FSS Act Sec 31 - Mandatory 14-Digit FSSAI License / Registration Number with Logo",
            "extracted_value": fssai,
            "pass": bool(re.search(r"\b[0-9]{14}\b", fssai)),
            "status": "Verified" if bool(re.search(r"\b[0-9]{14}\b", fssai)) else "Missing",
            "severity": "Critical",
            "penalty": 50000.00,
            "message": f"Valid 14-digit FSSAI License Number verified: {fssai}" if bool(re.search(r"\b[0-9]{14}\b", fssai)) else "Missing mandatory 14-digit FSSAI License or Registration Number under Food Safety Act."
        },
        {
            "category": "Packaged Food Regulations (FSSAI)",
            "rule_id": "FOOD_RULE_VEG_LOGO",
            "field": "Veg / Non-Veg Indicator",
            "rule_name": "FSSAI Labelling Reg 2.2.2.4 - Mandatory Vegetarian (Green Dot) or Non-Veg (Brown Triangle) Symbol",
            "extracted_value": veg_nonveg,
            "pass": veg_nonveg.lower() in ["vegetarian", "non-vegetarian", "veg", "non-veg"],
            "status": "Verified" if veg_nonveg.lower() in ["vegetarian", "non-vegetarian", "veg", "non-veg"] else "Missing",
            "severity": "Critical",
            "penalty": 25000.00,
            "message": f"Food category symbol declared: {veg_nonveg}" if veg_nonveg else "Missing mandatory Vegetarian / Non-Vegetarian symbol on packaged food."
        },
        {
            "category": "Packaged Food Regulations (FSSAI)",
            "rule_id": "FOOD_RULE_INGREDIENTS",
            "field": "Ingredients List",
            "rule_name": "FSSAI Labelling Reg 2.2.2.2 - Ingredients List in Descending Order of Weight",
            "extracted_value": ingredients,
            "pass": len(ingredients) >= 6,
            "status": "Verified" if len(ingredients) >= 6 else "Missing",
            "severity": "High",
            "penalty": 20000.00,
            "message": "Complete list of ingredients declared." if len(ingredients) >= 6 else "Missing ingredients list on packaged food."
        },
        {
            "category": "Packaged Food Regulations (FSSAI)",
            "rule_id": "FOOD_RULE_NUTRITION",
            "field": "Nutritional Facts Panel",
            "rule_name": "FSSAI Labelling Reg 2.2.2.3 - Mandatory Nutritional Information Panel per 100g/Serving",
            "extracted_value": nutrition,
            "pass": len(nutrition) >= 8 and any(k in nutrition.lower() for k in ["energy", "protein", "fat", "kcal", "carb"]),
            "status": "Verified" if (len(nutrition) >= 8 and any(k in nutrition.lower() for k in ["energy", "protein", "fat", "kcal", "carb"])) else "Missing",
            "severity": "High",
            "penalty": 25000.00,
            "message": "Nutritional values panel verified." if (len(nutrition) >= 8 and any(k in nutrition.lower() for k in ["energy", "protein", "fat", "kcal", "carb"])) else "Missing or incomplete nutritional facts panel on food package."
        },
        {
            "category": "Packaged Food Regulations (FSSAI)",
            "rule_id": "FOOD_RULE_EXPIRY",
            "field": "Expiry / Best Before Date",
            "rule_name": "FSSAI Labelling Reg 2.2.2.10 - Mandatory Best Before / Use By / Expiry Date",
            "extracted_value": expiry,
            "pass": len(expiry) >= 3,
            "status": "Verified" if len(expiry) >= 3 else "Missing",
            "severity": "Critical",
            "penalty": 30000.00,
            "message": f"Best before / expiry duration declared: {expiry}" if len(expiry) >= 3 else "Missing mandatory 'Best Before' or 'Use By' expiry date on packaged food."
        },
        {
            "category": "Packaged Food Regulations (FSSAI)",
            "rule_id": "FOOD_RULE_BATCH",
            "field": "Batch / Lot Identification",
            "rule_name": "FSSAI Labelling Reg 2.2.2.8 - Traceable Batch / Lot / Code Identification Number",
            "extracted_value": batch,
            "pass": len(batch) >= 2,
            "status": "Verified" if len(batch) >= 2 else "Missing",
            "severity": "Medium",
            "penalty": 15000.00,
            "message": f"Traceable batch/lot identification verified: {batch}" if len(batch) >= 2 else "Missing batch/lot number for food recall traceability."
        },
        {
            "category": "Packaged Food Regulations (FSSAI)",
            "rule_id": "FOOD_RULE_ALLERGEN",
            "field": "Allergen Advisory",
            "rule_name": "FSSAI Labelling Reg 2020 - Food Allergen Declaration & Precautionary Advisory",
            "extracted_value": allergen or "Not stated / No allergen advisory detected",
            "pass": len(allergen) >= 3,
            "status": "Verified" if len(allergen) >= 3 else "Review Required",
            "severity": "Medium",
            "penalty": 10000.00,
            "message": f"Allergen statement: {allergen}" if len(allergen) >= 3 else "No allergen advisory detected on packaging (required if containing common food allergens)."
        },
        {
            "category": "Packaged Food Regulations (FSSAI)",
            "rule_id": "FOOD_RULE_STORAGE",
            "field": "Storage Condition Instructions",
            "rule_name": "FSSAI Labelling Reg 2.2.2.11 - Mandatory Storage Condition Instructions for Food Safety",
            "extracted_value": storage or "Not stated",
            "pass": len(storage) >= 4,
            "status": "Verified" if len(storage) >= 4 else "Review Required",
            "severity": "Low",
            "penalty": 5000.00,
            "message": f"Storage directions: {storage}" if len(storage) >= 4 else "Specific storage condition instructions not clearly declared."
        }
    ]

    passed_count = sum(1 for r in rules_evaluation if r["pass"])
    total_rules = len(rules_evaluation)
    compliance_score = round((passed_count / total_rules) * 100, 1)

    violations = []
    for r in rules_evaluation:
        if not r["pass"] and r["status"] == "Missing":
            violations.append({
                "rule_id": r["rule_id"],
                "rule_name": r["rule_name"],
                "field_name": r["field"],
                "category": r["category"],
                "severity": r["severity"],
                "penalty_amount": r["penalty"],
                "notes": r["message"]
            })

    # Strict 3-state verdict
    critical_missing = [v for v in violations if v["severity"] == "Critical"]

    if passed_count >= 14 and len(critical_missing) == 0:
        overall_status = "COMPLIANT"
        risk_level = "LOW"
    elif passed_count >= 8 and len(critical_missing) <= 2:
        overall_status = "POTENTIAL_NON_COMPLIANCE"
        risk_level = "MEDIUM" if len(critical_missing) == 0 else "HIGH"
    else:
        overall_status = "REVIEW_REQUIRED"
        risk_level = "HIGH"

    # Split rules by category for organized display
    metrology_rules = [r for r in rules_evaluation if r["category"] == "Legal Metrology (Rules 2011)"]
    food_rules = [r for r in rules_evaluation if r["category"] == "Packaged Food Regulations (FSSAI)"]

    return {
        "overall_status": overall_status,
        "risk_level": risk_level,
        "compliance_score": compliance_score,
        "passed_declarations": passed_count,
        "total_declarations": total_rules,
        "metrology_rules": metrology_rules,
        "food_rules": food_rules,
        "rules_evaluation": rules_evaluation,
        "violations": violations
    }

