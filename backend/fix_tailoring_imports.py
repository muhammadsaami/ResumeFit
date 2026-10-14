#!/usr/bin/env python
with open('app/services/tailoring.py', 'r') as f:
    content = f.read()

# Fix 1: Remove TailorRecommendation from import (dead import)
old1 = """from ..models import (
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

new1 = """from ..models import (
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

if old1 in content:
    content = content.replace(old1, new1)
    print('Fixed import 1: removed TailorRecommendation')
else:
    print('Import 1 not found')

# Fix 2: Remove known_skill_terms import (dead import - only appears on import line)
old2 = 'from ..services.taxonomy import known_skill_terms'
# Check if it's used in code body after the import
after_import = content.split(old2)[1] if old2 in content else ''
used_in_body = 'known_skill_terms' in after_import
if not used_in_body:
    content = content.replace(old2, '')
    print('Fixed import 2: removed known_skill_terms')
else:
    print('kept known_skill_terms - used in body')

with open('app/services/tailoring.py', 'w') as f:
    f.write(content)
print('Done fixing tailoring.py imports')