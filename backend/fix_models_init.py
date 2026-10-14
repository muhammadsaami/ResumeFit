#!/usr/bin/env python
with open('app/models/__init__.py', 'r') as f:
    content = f.read()

# Add ChangeEditRequest to the tailoring imports
old_tailoring = """from .tailoring import (
    ChangeAction,
    ChangeCategory,
    ChangeDecisionResponse,
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
    print('Added ChangeEditRequest to app/models/__init__.py')
else:
    print('Old tailoring block not found')

with open('app/models/__init__.py', 'w') as f:
    f.write(content)