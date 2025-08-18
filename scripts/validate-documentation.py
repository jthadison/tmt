#!/usr/bin/env python3
"""
Documentation Validation Script

This script validates the TMT documentation structure, links, and formatting
to ensure comprehensive coverage and consistency.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set
import yaml
import argparse

class DocumentationValidator:
    def __init__(self, docs_root: Path):
        self.docs_root = docs_root
        self.errors = []
        self.warnings = []
        self.found_files = set()
        self.referenced_files = set()
        
    def validate_all(self) -> bool:
        """Run all validation checks"""
        print("Starting comprehensive documentation validation...")
        
        # Core validation checks
        self.validate_structure()
        self.validate_file_formats()
        self.validate_links()
        self.validate_cross_references()
        self.validate_coverage()
        self.validate_standards_compliance()
        
        # Report results
        self.print_results()
        
        return len(self.errors) == 0
    
    def validate_structure(self):
        """Validate expected documentation structure"""
        print("Validating documentation structure...")
        
        required_sections = [
            'technical',
            'operations', 
            'business',
            'compliance',
            'testing'
        ]
        
        for section in required_sections:
            section_path = self.docs_root / section
            if not section_path.exists():
                self.errors.append(f"Missing required section: {section}")
            elif not (section_path / 'index.md').exists():
                self.errors.append(f"Missing index.md in section: {section}")
        
        # Validate subsection structure
        self.validate_technical_structure()
        self.validate_operations_structure()
        self.validate_business_structure()
        self.validate_compliance_structure()
        self.validate_testing_structure()
    
    def validate_technical_structure(self):
        """Validate technical documentation structure"""
        tech_path = self.docs_root / 'technical'
        if not tech_path.exists():
            return
            
        required_subsections = [
            'system-architecture',
            'algorithms',
            'api',
            'database'
        ]
        
        for subsection in required_subsections:
            subsection_path = tech_path / subsection
            if not subsection_path.exists():
                self.warnings.append(f"Missing technical subsection: {subsection}")
    
    def validate_operations_structure(self):
        """Validate operations documentation structure"""
        ops_path = self.docs_root / 'operations'
        if not ops_path.exists():
            return
            
        required_subsections = [
            'manual',
            'risk-management',
            'monitoring',
            'user-guide'
        ]
        
        for subsection in required_subsections:
            subsection_path = ops_path / subsection
            if not subsection_path.exists():
                self.warnings.append(f"Missing operations subsection: {subsection}")
    
    def validate_business_structure(self):
        """Validate business documentation structure"""
        business_path = self.docs_root / 'business'
        if not business_path.exists():
            return
            
        required_subsections = [
            'requirements',
            'user-manual',
            'change-management',
            'training'
        ]
        
        for subsection in required_subsections:
            subsection_path = business_path / subsection
            if not subsection_path.exists():
                self.warnings.append(f"Missing business subsection: {subsection}")
    
    def validate_compliance_structure(self):
        """Validate compliance documentation structure"""
        compliance_path = self.docs_root / 'compliance'
        if not compliance_path.exists():
            return
            
        required_subsections = [
            'regulatory',
            'market',
            'privacy',
            'audit'
        ]
        
        for subsection in required_subsections:
            subsection_path = compliance_path / subsection
            if not subsection_path.exists():
                self.warnings.append(f"Missing compliance subsection: {subsection}")
    
    def validate_testing_structure(self):
        """Validate testing documentation structure"""
        testing_path = self.docs_root / 'testing'
        if not testing_path.exists():
            return
            
        required_subsections = [
            'strategy',
            'unit',
            'integration',
            'uat',
            'performance',
            'security'
        ]
        
        for subsection in required_subsections:
            subsection_path = testing_path / subsection
            if not subsection_path.exists():
                self.warnings.append(f"Missing testing subsection: {subsection}")
    
    def validate_file_formats(self):
        """Validate markdown file formatting"""
        print("📝 Validating file formats...")
        
        markdown_files = list(self.docs_root.rglob('*.md'))
        self.found_files = {str(f.relative_to(self.docs_root)) for f in markdown_files}
        
        for md_file in markdown_files:
            self.validate_markdown_file(md_file)
    
    def validate_markdown_file(self, file_path: Path):
        """Validate individual markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required elements
            if not content.strip():
                self.errors.append(f"Empty file: {file_path.relative_to(self.docs_root)}")
                return
            
            # Check for title (H1)
            if not re.search(r'^# .+', content, re.MULTILINE):
                self.warnings.append(f"Missing title (H1) in: {file_path.relative_to(self.docs_root)}")
            
            # Check for multiple H1s (should only have one)
            h1_count = len(re.findall(r'^# .+', content, re.MULTILINE))
            if h1_count > 1:
                self.warnings.append(f"Multiple H1 titles in: {file_path.relative_to(self.docs_root)}")
            
            # Check for proper heading hierarchy
            self.validate_heading_hierarchy(file_path, content)
            
        except Exception as e:
            self.errors.append(f"Error reading file {file_path.relative_to(self.docs_root)}: {e}")
    
    def validate_heading_hierarchy(self, file_path: Path, content: str):
        """Validate markdown heading hierarchy"""
        headings = re.findall(r'^(#{1,6}) (.+)', content, re.MULTILINE)
        prev_level = 0
        
        for heading_marks, heading_text in headings:
            current_level = len(heading_marks)
            
            # Check for heading level jumps (e.g., H1 -> H3)
            if current_level > prev_level + 1:
                self.warnings.append(
                    f"Heading level jump in {file_path.relative_to(self.docs_root)}: "
                    f"H{prev_level} -> H{current_level} ('{heading_text}')"
                )
            
            prev_level = current_level
    
    def validate_links(self):
        """Validate internal links in documentation"""
        print("🔗 Validating internal links...")
        
        markdown_files = list(self.docs_root.rglob('*.md'))
        
        for md_file in markdown_files:
            self.validate_links_in_file(md_file)
    
    def validate_links_in_file(self, file_path: Path):
        """Validate links in a specific file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find markdown links [text](url)
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
            
            for link_text, link_url in links:
                # Skip external links (http/https)
                if link_url.startswith(('http://', 'https://')):
                    continue
                
                # Skip anchors within same page
                if link_url.startswith('#'):
                    continue
                
                # Resolve relative link
                if link_url.startswith('/'):
                    # Absolute path from docs root
                    target_path = self.docs_root / link_url.lstrip('/')
                else:
                    # Relative path from current file
                    target_path = file_path.parent / link_url
                
                # Normalize path
                try:
                    target_path = target_path.resolve()
                    
                    # Check if target exists
                    if not target_path.exists():
                        self.errors.append(
                            f"Broken link in {file_path.relative_to(self.docs_root)}: "
                            f"'{link_text}' -> '{link_url}'"
                        )
                    else:
                        # Track referenced files
                        if target_path.is_file() and target_path.suffix == '.md':
                            rel_path = str(target_path.relative_to(self.docs_root))
                            self.referenced_files.add(rel_path)
                            
                except Exception as e:
                    self.errors.append(
                        f"Invalid link in {file_path.relative_to(self.docs_root)}: "
                        f"'{link_text}' -> '{link_url}' ({e})"
                    )
                    
        except Exception as e:
            self.errors.append(f"Error validating links in {file_path.relative_to(self.docs_root)}: {e}")
    
    def validate_cross_references(self):
        """Validate cross-references between documentation sections"""
        print("🔄 Validating cross-references...")
        
        # Key documents that should be referenced
        key_documents = {
            'technical/system-architecture/overview.md': 'System Architecture',
            'operations/risk-management/risk-parameters.md': 'Risk Parameters',
            'compliance/regulatory/us-requirements.md': 'US Regulations',
            'testing/strategy/test-strategy.md': 'Test Strategy'
        }
        
        for doc_path, doc_name in key_documents.items():
            if doc_path not in self.referenced_files:
                self.warnings.append(f"Key document not referenced: {doc_name} ({doc_path})")
    
    def validate_coverage(self):
        """Validate documentation coverage of system components"""
        print("📊 Validating documentation coverage...")
        
        # Check for orphaned files (not referenced by any other file)
        orphaned_files = self.found_files - self.referenced_files - {'index.md'}
        
        for orphaned in orphaned_files:
            # Skip certain files that don't need to be referenced
            if not any(orphaned.startswith(skip) for skip in ['README', 'CHANGELOG', 'LICENSE']):
                self.warnings.append(f"Orphaned file (not referenced): {orphaned}")
        
        # Validate that all major system components are documented
        required_components = [
            'Circuit Breaker Agent',
            'Market Analysis Agent', 
            'Risk Management Agent',
            'Anti-Correlation Agent',
            'Personality Engine',
            'Performance Tracker',
            'Compliance Agent',
            'Learning Safety Agent'
        ]
        
        # Check if components are mentioned in documentation
        all_content = ""
        for md_file in self.docs_root.rglob('*.md'):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    all_content += f.read().lower()
            except:
                continue
        
        for component in required_components:
            if component.lower() not in all_content:
                self.warnings.append(f"System component not documented: {component}")
    
    def validate_standards_compliance(self):
        """Validate compliance with documentation standards"""
        print("📋 Validating standards compliance...")
        
        # Check for consistent formatting in index files
        index_files = list(self.docs_root.rglob('index.md'))
        
        for index_file in index_files:
            self.validate_index_file_standards(index_file)
    
    def validate_index_file_standards(self, index_file: Path):
        """Validate index file follows standards"""
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required sections in index files
            required_sections = ['Documentation Structure', 'Quick Reference']
            
            for section in required_sections:
                if section not in content:
                    self.warnings.append(
                        f"Missing section '{section}' in index: {index_file.relative_to(self.docs_root)}"
                    )
            
        except Exception as e:
            self.errors.append(f"Error validating index file {index_file.relative_to(self.docs_root)}: {e}")
    
    def print_results(self):
        """Print validation results"""
        print("\n" + "="*60)
        print("📋 DOCUMENTATION VALIDATION RESULTS")
        print("="*60)
        
        if not self.errors and not self.warnings:
            print("✅ All validation checks passed!")
            print(f"📄 Validated {len(self.found_files)} documentation files")
            print(f"🔗 Checked {len(self.referenced_files)} cross-references")
            return
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        print(f"\n📊 SUMMARY:")
        print(f"  Files found: {len(self.found_files)}")
        print(f"  Files referenced: {len(self.referenced_files)}")
        print(f"  Errors: {len(self.errors)}")
        print(f"  Warnings: {len(self.warnings)}")
        
        if self.errors:
            print(f"\n❌ Validation FAILED - {len(self.errors)} errors must be fixed")
        else:
            print(f"\n✅ Validation PASSED - {len(self.warnings)} warnings to consider")

def main():
    parser = argparse.ArgumentParser(description='Validate TMT documentation')
    parser.add_argument('--docs-root', type=Path, default=Path('docs'),
                       help='Path to documentation root directory')
    parser.add_argument('--strict', action='store_true',
                       help='Treat warnings as errors')
    
    args = parser.parse_args()
    
    if not args.docs_root.exists():
        print(f"❌ Documentation directory not found: {args.docs_root}")
        sys.exit(1)
    
    validator = DocumentationValidator(args.docs_root)
    success = validator.validate_all()
    
    if args.strict and validator.warnings:
        print("\n❌ Strict mode: treating warnings as errors")
        success = False
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()