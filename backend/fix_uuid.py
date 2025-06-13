#!/usr/bin/env python3
"""
Quick fix to replace UUID with String for SQLite compatibility
"""

import os
import re

def fix_uuid_in_file(filepath):
    """Fix UUID imports and usage in a file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace UUID imports
    content = re.sub(r'from sqlalchemy\.dialects\.postgresql import UUID', 
                     'from sqlalchemy import String', content)
    
    # Replace UUID column definitions
    content = re.sub(r'Column\(UUID\(as_uuid=True\)', 'Column(String(36)', content)
    content = re.sub(r'Column\(UUID\(\)', 'Column(String(36)', content)
    
    # Replace ForeignKey UUID references
    content = re.sub(r'UUID\(as_uuid=True\), ForeignKey', 'String(36), ForeignKey', content)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Fixed UUID in {filepath}")

# Fix all model files
model_files = [
    'db/models/project.py',
    'db/models/structural.py', 
    'db/models/analysis.py',
    'db/models/design.py',
    'db/models/bim.py'
]

for model_file in model_files:
    if os.path.exists(model_file):
        fix_uuid_in_file(model_file)

print("UUID fixes completed!")