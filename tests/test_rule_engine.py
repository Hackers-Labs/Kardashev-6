"""
Statutory Rule Engine Test Suite
Verifies:
1. Legal Metrology (Packaged Commodities) Rules, 2011 (Rule 6).
2. FSSAI Packaged Food Labelling Regulations.
3. Unit standards, MRP, date formats, and penalty determinations.
"""

import unittest
from services.rule_engine import evaluate_declarations

class TestRuleEngine(unittest.TestCase):

    def setUp(self):
        self.compliant_sample = {
            "manufacturer": "Hindustan Foods Ltd, Plot 42, GIDC, Vapi, Gujarat - 396195",
            "product_name": "Premium Whole Wheat Atta",
            "net_quantity": "5 kg",
            "mrp": "MRP ₹ 245.00 (incl. of all taxes)",
            "unit_sale_price": "₹ 49.00 / kg",
            "manufacturing_date": "08/2026",
            "consumer_care_phone": "1800-22-1234",
            "consumer_care_email": "customercare@hindustanfoods.com",
            "country_of_origin": "India",
            "fssai_license": "10015021000248",
            "veg_nonveg": "Vegetarian",
            "ingredients": "Whole Wheat Grain (100%)",
            "nutritional_info": "Energy: 340 kcal, Protein: 12g, Carbohydrates: 71g",
            "expiry_or_best_before": "Best before 6 months from packaging",
            "batch_number": "BATCH-2026-W42",
            "allergen_warning": "Contains wheat (gluten)",
            "storage_instructions": "Store in a cool, hygienic and dry place"
        }

    def test_compliant_package(self):
        """A fully compliant food package must score 100% and return COMPLIANT."""
        result = evaluate_declarations(self.compliant_sample)
        self.assertEqual(result["overall_status"], "COMPLIANT")
        self.assertEqual(result["compliance_score"], 100.0)
        self.assertEqual(len(result["violations"]), 0)

    def test_missing_mrp_violation(self):
        """Missing MRP must trigger critical violation under Rule 6(1)(e)."""
        sample = dict(self.compliant_sample)
        sample["mrp"] = ""
        result = evaluate_declarations(sample)

        self.assertIn(result["overall_status"], ["POTENTIAL_NON_COMPLIANCE", "REVIEW_REQUIRED"])
        self.assertLess(result["compliance_score"], 100.0)
        mrp_viols = [v for v in result["violations"] if "mrp" in v["field_name"].lower() or "price" in v["rule_name"].lower()]
        self.assertTrue(len(mrp_viols) > 0, "Missing MRP must be flagged as a statutory violation.")

    def test_missing_net_quantity_violation(self):
        """Missing net quantity must trigger critical violation under Rule 6(1)(c)."""
        sample = dict(self.compliant_sample)
        sample["net_quantity"] = ""
        result = evaluate_declarations(sample)

        self.assertNotEqual(result["overall_status"], "COMPLIANT")
        qty_viols = [v for v in result["violations"] if "quantity" in v["field_name"].lower() or "quantity" in v["rule_name"].lower()]
        self.assertTrue(len(qty_viols) > 0, "Missing net quantity must be flagged.")

    def test_missing_manufacturer_address(self):
        """Missing manufacturer address must trigger violation under Rule 6(1)(a)."""
        sample = dict(self.compliant_sample)
        sample["manufacturer"] = ""
        result = evaluate_declarations(sample)

        self.assertNotEqual(result["overall_status"], "COMPLIANT")
        mfr_viols = [v for v in result["violations"] if "manufacturer" in v["field_name"].lower() or "address" in v["rule_name"].lower()]
        self.assertTrue(len(mfr_viols) > 0, "Missing manufacturer address must be flagged.")

    def test_invalid_fssai_license_length(self):
        """FSSAI license must be exactly 14 digits; invalid length should be flagged."""
        sample = dict(self.compliant_sample)
        sample["fssai_license"] = "12345"  # invalid length
        result = evaluate_declarations(sample)

        fssai_rule = next((r for r in result["rules_evaluation"] if r["rule_id"] == "FOOD_RULE_FSSAI"), None)
        self.assertIsNotNone(fssai_rule)
        self.assertFalse(fssai_rule["pass"])

if __name__ == "__main__":
    unittest.main()
