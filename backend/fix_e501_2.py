#!/usr/bin/env python
import os
path = r'C:\Users\khans\OneDrive\Desktop\Resume project\backend\app/services/tailoring.py'
with open(path, 'r') as f:
    content = f.read()

# Fix 1: Break the long function signature line
old1 = 'def analyze_job_description(structured: StructuredResume, jd_text: str, resume_text: str) -> TailorAnalysis:'
new1 = '''def analyze_job_description(structured: StructuredResume,
    jd_text: str,
    resume_text: str) -> TailorAnalysis:'''

if old1 in content:
    content = content.replace(old1, new1)
    print('Fixed analyze_job_description line length')
else:
    print('old1 not found')

# Fix 2: Break the match_percentage line
old2 = 'match_percentage = _calculate_match_percentage(required_matched, required_total) if required_total else 100'
new2 = '''if required_total:
    match_percentage = _calculate_match_percentage(required_matched, required_total)
else:
    match_percentage = 100'''

if old2 in content:
    content = content.replace(old2, new2)
    print('Fixed match_percentage line length')
else:
    print('old2 not found')

with open(path, 'w') as f:
    f.write(content)
print('Done fixing E501 errors')