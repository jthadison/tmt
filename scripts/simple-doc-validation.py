#!/usr/bin/env python3
"""Simple documentation validation for TMT system"""

import os
from pathlib import Path

def validate_documentation():
    """Validate basic documentation structure"""
    docs_root = Path('docs')
    
    if not docs_root.exists():
        print("ERROR: docs directory not found")
        return False
    
    print("Starting documentation validation...")
    
    # Check main index
    main_index = docs_root / 'index.md'
    if main_index.exists():
        print("[OK] Main documentation index found")
    else:
        print("[ERROR] Main documentation index missing")
        return False
    
    # Check required sections
    required_sections = [
        'technical',
        'operations', 
        'business',
        'compliance',
        'testing'
    ]
    
    all_good = True
    
    for section in required_sections:
        section_path = docs_root / section
        index_path = section_path / 'index.md'
        
        if section_path.exists() and index_path.exists():
            print(f"[OK] {section} section complete")
        elif section_path.exists():
            print(f"[WARN] {section} section exists but missing index.md")
        else:
            print(f"[ERROR] {section} section missing")
            all_good = False
    
    # Count total documentation files
    md_files = list(docs_root.rglob('*.md'))
    print(f"\nTotal documentation files: {len(md_files)}")
    
    # List all created files
    print("\nCreated documentation files:")
    for md_file in sorted(md_files):
        rel_path = md_file.relative_to(docs_root)
        print(f"  - {rel_path}")
    
    if all_good:
        print("\n[SUCCESS] Documentation validation passed!")
        return True
    else:
        print("\n[FAILED] Documentation validation failed!")
        return False

if __name__ == '__main__':
    validate_documentation()