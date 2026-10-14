#!/usr/bin/env python
import os
path = r'C:\Users\khans\OneDrive\Desktop\Resume project\backend\app/services/tailoring.py'
with open(path, 'r') as f:
    content = f.read()

# Add from __future__ import annotations at the top
if 'from __future__ import annotations' not in content:
    content = 'from __future__ import annotations\n' + content
    with open(path, 'w') as f:
        f.write(content)
    print('Added from __future__ import annotations')
else:
    print('Already has future annotations')