#!/usr/bin/env python
import os
path = r'C:\Users\khans\OneDrive\Desktop\Resume project\backend\app/services/tailoring.py'
with open(path, 'r') as f:
    content = f.read()

# Add analyze_job_description function before _tailor_analysis
new_function = '''

def analyze_job_description(structured: StructuredResume, jd_text: str, resume_text: str) -> TailorAnalysis:
    \"\"\"Analyze a resume against a job description.
    
    Returns a TailorAnalysis with match percentage, matched/missing skills,
    and human-readable explanations.
    \"\"\"
    return _tailor_analysis(structured, jd_text, resume_text)
'''

# Insert before _tailor_analysis
if 'def _tailor_analysis' in content:
    content = content.replace('def _tailor_analysis', new_function + 'def _tailor_analysis')
    with open(path, 'w') as f:
        f.write(content)
    print('Added analyze_job_description function')
else:
    print('Could not find _tailor_analysis function')