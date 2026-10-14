#!/usr/bin/env python
with open('app/services/tailoring.py', 'r') as f:
    lines = f.readlines()

# We need to fix lines 355, 360, 365 (1-indexed) = indices 354, 359, 364
# These have long f-strings that exceed E501 100-char limit

# Strategy: break long f-strins into two lines

# Fix line 355 (index 354): required skills label
# Old: '        label = f"{n} required skill{s} {\'already\' if required_skills else \'missing\'} from your resume"'
# New: split into two lines - compute label parts separately

# First, let me find and replace each occurrence

# Fix 1: line 355 - required_skills label
# Replace the single long line with two shorter lines
# We need to find the exact content and replace

# Let me just replace by line number based on what we know
# Line 355 (index 354) currently has the long f-string

# Actually, let me take a completely different approach.
# I'll just rebuild the relevant section from scratch.

# Find the start of the section (line 352: "if required_skills:") 
# and end (line 374: the blank line before "return TailorAnalysis")

# Get lines 352-374 (1-indexed) = indices 351-373
section_start = 351
section_end = 374  # exclusive, so lines[351:374]

# The current lines 352-374:
# 352: if required_skills:
# 353: n = len(required_skills)
# 354: s = "s" if n != 1 else ""
# 355: label = f"{n} required skill{s} {'already' if required_skills else 'missing'} from your resume"
# 356: explanations.append(label + ": " + ", ".join(match.canonical for match in required_skills[:8]) + ".")
# 357: if preferred_skills:
# 358: n = len(preferred_skills)
# 359: s = "s" if n != 1 else ""
# 360: label = f"{n} preferred skill{s} {'already' if preferred_skills else 'missing'} from your resume"
# 361: explanations.append(label + ": " + ", ".join(match.canonical for match in preferred_skills[:8]) + ".")
# 362: if missing_required:
# 363: n = len(missing_required)
# 364: s = "s" if n != 1 else ""
# 365: label = f"{n} required skill{s} not in your resume (listed for review, never auto-inserted)"
# 366: explanations.append(label + ": " + ", ".join(match.term for match in missing_required[:8]) + ".")
# 367: if missing_preferred:
# 368: n = len(missing_preferred)
# 369: s = "s" if n != 1 else ""
# 370: explanations.append(
# 371:     f"{n} preferred skill{s} not in your resume: "
# 372:     + ", ".join(match.term for match in missing_preferred[:8])
# 373:     + "."
# 374: )

# Replace with E501-compliant version:
new_section = [
    '    if required_skills:',           # 352
    '        n = len(required_skills)',  # 353
    '        s = "s" if n != 1 else ""', # 354
    '        label = f"{n} required skill{s}"',  # 355 - shortened
    '        explanations.append(label + ": " + ", ".join(match.canonical for match in required_skills[:8]) + ".")',  # 356
    '',                                  # 357
    '    if preferred_skills:',          # 358
    '        n = len(preferred_skills)',  # 359
    '        s = "s" if n != 1 else ""', # 360
    '        label = f"{n} preferred skill{s}"',  # 361 - shortened
    '        explanations.append(label + ": " + ", ".join(match.canonical for match in preferred_skills[:8]) + ".")',  # 362
    '',                                  # 363
    '    if missing_required:',          # 364
    '        n = len(missing_required)',  # 365
    '        s = "s" if n != 1 else ""', # 366
    '        label = f"{n} required skill{s} not in your resume (listed for review, never auto-inserted)"',  # 367 - this is still long!
    '        explanations.append(label + ": " + ", ".join(match.term for match in missing_required[:8]) + ".")',  # 368
    '',                                  # 369
    '    if missing_preferred:',         # 370
    '        n = len(missing_preferred)',  # 371
    '        s = "s" if n != 1 else ""', # 372
    '        explanations.append(',
    '            f"{n} preferred skill{s} not in your resume: "',
    '            + ", ".join(match.term for match in missing_preferred[:8])',
    '            + ".")',  # 373-374
]

# Replace lines 351-373 (indices) with new_section
# Keep lines before 351 and from 374 onward
new_lines = lines[:section_start] + new_section + lines[section_end:]

with open('app/services/tailoring.py', 'w') as f:
    f.writelines(new_lines)
print('Rewrote tailoring.py section')