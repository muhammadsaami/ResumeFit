#!/usr/bin/env python
import os
path = r'C:\Users\khans\OneDrive\Desktop\Resume project\backend\app/models/tailoring.py'
with open(path, 'r') as f:
    content = f.read()

# Add RequirementClassification at the end of the file
if 'RequirementClassification' not in content:
    content += '''

from typing import TypedDict

class RequirementClassification(TypedDict):
    """Classification of a skill/keyword as required or preferred."""
    pass
'''
    with open(path, 'w') as f:
        f.write(content)
    print('Added RequirementClassification to app/models/tailoring.py')
else:
    print('Already exists')