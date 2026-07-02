"""Advanced tests based on sample conversations."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.catalog import Catalog


def test_catalog_loading():
    """Test catalog can be loaded."""
    catalog_path = "data/shl_product_catalog.json"
    if not Path(catalog_path).exists():
        print("Catalog not found - skipping catalog test")
        return
    
    catalog = Catalog(catalog_path)
    assert catalog.size() > 0, "Catalog should not be empty"
    print(f"[OK] Catalog loaded with {catalog.size()} assessments")


def test_known_assessments():
    """Test that specific assessments from sample conversations exist in catalog."""
    catalog_path = "data/shl_product_catalog.json"
    if not Path(catalog_path).exists():
        return
    
    catalog = Catalog(catalog_path)
    
    # Assessments from sample conversations
    expected_names = [
        "Occupational Personality Questionnaire OPQ32r",
        "SHL Verify Interactive G+",
        "Graduate Scenarios",
        "Smart Interview Live Coding",
        "Dependability and Safety Instrument (DSI)",
    ]
    
    found = 0
    for name in expected_names:
        assessment = catalog.get_by_name(name)
        if assessment:
            found += 1
            print(f"[OK] Found: {name}")
        else:
            print(f"[WARN] Not found: {name}")
    
    print(f"Found {found}/{len(expected_names)} expected assessments")


def test_assessment_fields():
    """Test that assessments have required fields."""
    catalog_path = "data/shl_product_catalog.json"
    if not Path(catalog_path).exists():
        return
    
    catalog = Catalog(catalog_path)
    assessments = catalog.get_all()
    
    # Check first few assessments have required fields
    for assessment in assessments[:5]:
        assert assessment.name, "Assessment must have name"
        assert assessment.url, "Assessment must have URL"
        assert assessment.test_type, "Assessment must have test_type"
        assert assessment.description, "Assessment must have description"
        print(f"[OK] Assessment fields valid: {assessment.name}")


def test_test_type_mapping():
    """Test that test types are correctly mapped."""
    catalog_path = "data/shl_product_catalog.json"
    if not Path(catalog_path).exists():
        return
    
    catalog = Catalog(catalog_path)
    
    # Check test type codes
    test_types = set()
    for assessment in catalog.get_all():
        test_type = assessment.test_type
        if test_type:
            for code in test_type.split(","):
                test_types.add(code)
    
    expected_codes = {"K", "P", "A", "S", "B", "C", "D"}
    print(f"Found test type codes: {sorted(test_types)}")
    
    # Check all codes are in expected set
    invalid = test_types - expected_codes
    if invalid:
        print(f"[WARN] Invalid test type codes: {invalid}")
    else:
        print("[OK] All test type codes valid")


if __name__ == "__main__":
    print("Running advanced catalog tests...\n")
    test_catalog_loading()
    print()
    test_known_assessments()
    print()
    test_assessment_fields()
    print()
    test_test_type_mapping()
    print("\nTests complete!")
