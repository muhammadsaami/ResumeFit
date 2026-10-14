#!/usr/bin/env python
with open('app/models/__init__.py', 'r') as f:
    content = f.read()

# Remove SkillMatch and MatchMetadata from tailoring imports - they're not defined in app/models/tailoring.py
old_tailoring = """from .tailoring import (
    ChangeAction,
    ChangeCategory,
    ChangeDecisionResponse,
    ChangeEditRequest,
    ChangeListResponse,
    ChangeOrigin,
    ChangeStatus,
    ChangeSummary,
    GuardStatus,
    JobDescriptionStats,
    KeywordMatch,
    MatchMetadata,
    ResumeChange,
    SkillMatch,
    ResumeChange,
    TailorRequest,
    TailorResponse,
)"""

new_tailoring = """from .tailoring import (
    ChangeAction,
    ChangeCategory,
    ChangeDecisionResponse,
    ChangeEditRequest,
    ChangeListResponse,
    ChangeOrigin,
    ChangeStatus,
    ChangeSummary,
    GuardStatus,
    JobDescriptionStats,
    KeywordMatch,
    ResumeChange,
    TailorRequest,
    TailorResponse,
)"""

if old_tailoring in content:
    content = content.replace(old_tailoring, new_tailoring)
    print('Removed SkillMatch and MatchMetadata from app/models/__init__.py')
else:
    print('Old tailoring block not found')

with open('app/models/__init__.py', 'w') as f:
    f.write(content)