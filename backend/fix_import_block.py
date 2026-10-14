#!/usr/bin/env python
import os
path = r'C:\Users\khans\OneDrive\Desktop\Resume project\backend\app/services/tailoring.py'
with open(path, 'r') as f:
    content = f.read()

# Replace the entire import block
old_import_block = """import re
from typing import Any, Optional

from ..models import (
    StructuredResume,

    ChangeCategory,

    ChangeOrigin,

    ResumeChange,

    ChangeDecisionResponse,

    ChangeEditRequest,

    SkillMatch,
    MatchMetadata,

    RequirementClassification,
)"""

new_import_block = """import re
from typing import Any, Optional

from ..models import (
    StructuredResume,
    ChangeCategory,
    ChangeOrigin,
    ResumeChange,
    ChangeDecisionResponse,
    ChangeEditRequest,
    RequirementClassification,
)"""

if old_import_block in content:
    content = content.replace(old_import_block, new_import_block)
    with open(path, 'w') as f:
        f.write(content)
    print('Replaced entire import block in tailoring.py')
else:
    print('Old import block not found')
    # Debug: print first 300 chars
    print('First 300 chars:', content[:300])