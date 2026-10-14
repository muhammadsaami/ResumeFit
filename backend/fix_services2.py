#!/usr/bin/env python
with open('app/services/tailoring.py', 'r') as f:
    content = f.read()

# Remove SkillMatch and MatchMetadata from import - they're used locally, not from models
old_import = """from ..models import (
    StructuredResume,
    ChangeCategory,
    ChangeOrigin,
    ResumeChange,
    ChangeDecisionResponse,
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
    RequirementClassification,
)"""

if old_import in content:
    content = content.replace(old_import, new_import)
    print('Removed SkillMatch and MatchMetadata from app/services/tailoring.py')
else:
    print('Import pattern not found')

with open('app/services/tailoring.py', 'w') as f:
    f.write(content)