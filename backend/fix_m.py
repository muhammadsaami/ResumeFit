#!/usr/bin/env python
import os
path = r'C:\Users\khans\OneDrive\Desktop\Resume project\backend\app/models/__init__.py'
with open(path, 'r') as f:
    content = f.read()

# Remove MatchMetadata and SkillMatch from tailoring imports
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
    with open(path, 'w') as f:
        f.write(content)
    print('Removed MatchMetadata and SkillMatch from app/models/__init__.py')
else:
    print('Old tailoring block not found')