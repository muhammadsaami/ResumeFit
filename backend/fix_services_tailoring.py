#!/usr/bin/env python
with open('app/services/tailoring.py', 'r') as f:
    content = f.read()

# Fix the import - remove dead imports, keep only what's in app/models/__init__.py
old_import = """from ..models import (
    StructuredResume,
    TailorRecommendation,
    ChangeCategory,
    ChangeOrigin,
    ResumeChange,
    ChangeDecisionResponse,
    ChangeEditRequest,
    SkillMatch,
    MatchMetadata,
    RequirementClassification,
)"""

new_import = """from ..models import (
    StructuredResume,
    ChangeCategory,
    ChangeOrigin,
    ResumeChange,
    ChangeDecisionResponse,
    SkillMatch,
    MatchMetadata,
    RequirementClassification,
)"""

if old_import in content:
    content = content.replace(old_import, new_import)
    print('Fixed app/services/tailoring.py imports')
else:
    print('Import pattern not found')

with open('app/services/tailoring.py', 'w') as f:
    f.write(content)