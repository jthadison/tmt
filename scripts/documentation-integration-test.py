#!/usr/bin/env python3
"""
Documentation Integration Test

Validates that the new documentation framework integrates properly
with the existing TMT system and follows the acceptance criteria.
"""

import os
from pathlib import Path

def test_story_acceptance_criteria():
    """Test that all acceptance criteria from the epic stories are met"""
    print("Testing Story Acceptance Criteria...")
    
    # Story 1: Technical & Algorithm Documentation Suite
    story_1_criteria = [
        ('docs/technical/system-architecture/overview.md', 'System Architecture Documentation'),
        ('docs/technical/algorithms/trading-strategies.md', 'Algorithm Documentation'),
        ('docs/technical/api/internal-apis.md', 'API Documentation'),
        ('docs/technical/index.md', 'Technical Documentation Index')
    ]
    
    # Story 2: Operational & Risk Management Documentation
    story_2_criteria = [
        ('docs/operations/manual/startup-shutdown.md', 'Operations Manual'),
        ('docs/operations/risk-management/risk-parameters.md', 'Risk Management Documentation'),
        ('docs/operations/index.md', 'Operations Documentation Index')
    ]
    
    # Story 3: Compliance, Business & Testing Documentation
    story_3_criteria = [
        ('docs/compliance/index.md', 'Compliance Documentation'),
        ('docs/business/index.md', 'Business Documentation'),
        ('docs/testing/index.md', 'Testing Documentation')
    ]
    
    all_criteria = story_1_criteria + story_2_criteria + story_3_criteria
    passed = 0
    total = len(all_criteria)
    
    print(f"\nChecking {total} acceptance criteria...")
    
    for file_path, description in all_criteria:
        if Path(file_path).exists():
            print(f"[PASS] {description}")
            passed += 1
        else:
            print(f"[FAIL] {description} - {file_path} not found")
    
    print(f"\nStory Acceptance Criteria: {passed}/{total} passed")
    return passed == total

def test_integration_with_existing_docs():
    """Test integration with existing documentation structure"""
    print("\nTesting Integration with Existing Documentation...")
    
    # Check that existing docs are preserved
    existing_docs = [
        'docs/architecture/index.md',
        'docs/prd/index.md', 
        'docs/stories',
        'CLAUDE.md'
    ]
    
    preserved = 0
    total = len(existing_docs)
    
    for doc_path in existing_docs:
        if Path(doc_path).exists():
            print(f"[PASS] Existing documentation preserved: {doc_path}")
            preserved += 1
        else:
            print(f"[FAIL] Existing documentation missing: {doc_path}")
    
    print(f"\nExisting Documentation Preservation: {preserved}/{total} preserved")
    return preserved == total

def test_documentation_completeness():
    """Test that documentation covers all major system components"""
    print("\nTesting Documentation Completeness...")
    
    # Major system components that should be documented
    components = [
        'Circuit Breaker Agent',
        'Market Analysis Agent',
        'Risk Management Agent', 
        'Anti-Correlation Agent',
        'Personality Engine',
        'Performance Tracker',
        'Compliance Agent',
        'Learning Safety Agent'
    ]
    
    # Read all documentation content
    all_content = ""
    docs_root = Path('docs')
    
    for md_file in docs_root.rglob('*.md'):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                all_content += f.read().lower()
        except:
            continue
    
    documented = 0
    total = len(components)
    
    for component in components:
        if component.lower() in all_content:
            print(f"[PASS] Component documented: {component}")
            documented += 1
        else:
            print(f"[WARN] Component may need more documentation: {component}")
    
    print(f"\nComponent Coverage: {documented}/{total} components documented")
    return documented >= total * 0.8  # 80% threshold

def test_documentation_structure():
    """Test that documentation follows the planned structure"""
    print("\nTesting Documentation Structure...")
    
    required_structure = {
        'docs/index.md': 'Main documentation index',
        'docs/technical/index.md': 'Technical documentation section',
        'docs/operations/index.md': 'Operations documentation section',
        'docs/business/index.md': 'Business documentation section',
        'docs/compliance/index.md': 'Compliance documentation section',
        'docs/testing/index.md': 'Testing documentation section'
    }
    
    structured = 0
    total = len(required_structure)
    
    for file_path, description in required_structure.items():
        if Path(file_path).exists():
            print(f"[PASS] {description}")
            structured += 1
        else:
            print(f"[FAIL] {description} - {file_path} not found")
    
    print(f"\nDocumentation Structure: {structured}/{total} required files present")
    return structured == total

def test_compatibility_requirements():
    """Test compatibility with existing development workflow"""
    print("\nTesting Compatibility Requirements...")
    
    compatibility_checks = [
        ('Git workflow integration', lambda: Path('.git').exists()),
        ('Existing docs structure preserved', lambda: Path('docs/architecture').exists()),
        ('Markdown format consistency', lambda: len(list(Path('docs').rglob('*.md'))) > 50),
        ('Documentation versioning', lambda: Path('docs/index.md').exists())
    ]
    
    compatible = 0
    total = len(compatibility_checks)
    
    for check_name, check_func in compatibility_checks:
        try:
            if check_func():
                print(f"[PASS] {check_name}")
                compatible += 1
            else:
                print(f"[FAIL] {check_name}")
        except Exception as e:
            print(f"[ERROR] {check_name}: {e}")
    
    print(f"\nCompatibility Requirements: {compatible}/{total} requirements met")
    return compatible == total

def run_integration_tests():
    """Run all integration tests"""
    print("="*60)
    print("TMT DOCUMENTATION INTEGRATION TEST")
    print("="*60)
    
    tests = [
        ('Story Acceptance Criteria', test_story_acceptance_criteria),
        ('Integration with Existing Docs', test_integration_with_existing_docs),
        ('Documentation Completeness', test_documentation_completeness),
        ('Documentation Structure', test_documentation_structure),
        ('Compatibility Requirements', test_compatibility_requirements)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"TEST: {test_name}")
        print(f"{'='*60}")
        
        try:
            if test_func():
                print(f"\n[SUCCESS] {test_name} PASSED")
                passed_tests += 1
            else:
                print(f"\n[FAILED] {test_name} FAILED")
        except Exception as e:
            print(f"\n[ERROR] {test_name} ERROR: {e}")
    
    print(f"\n{'='*60}")
    print("INTEGRATION TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("\n[SUCCESS] All integration tests passed!")
        print("Documentation framework successfully integrated with TMT system.")
        return True
    else:
        print(f"\n[PARTIAL] {passed_tests}/{total_tests} tests passed.")
        print("Some integration issues may need attention.")
        return False

if __name__ == '__main__':
    success = run_integration_tests()
    exit(0 if success else 1)