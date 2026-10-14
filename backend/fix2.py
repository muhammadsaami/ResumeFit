#!/usr/bin/env python
with open('app/services/tailoring.py', 'r') as f:
    content = f.read()

# The problem section is lines 352-374 (1-indexed)
# We need to replace lines 352-374 with properly indented, E501-compliant version

# First, find the exact boundaries
lines = content.split('\n')

# New content for lines 352-374 (1-indexed) = indices 351-373
new_lines = [
    '    if required_skills:',
    '        n = len(required_skills)',
    '        s = "s" if n != 1 else ""',
    "        label = f'{n} required skill{s} {\"already\" if required_skills else \"missing\"} from your resume'",
    '        explanations.append(label + ": " + ", ".join(match.canonical for match in required_skills[:8]) + ".")',
    '',
    '    if preferred_skills:',
    '        n = len(preferred_skills)',
    '        s = "s" if n != 1 else ""',
    "        label = f'{n} preferred skill{s} {\"already\" if preferred_skills else \"missing\"} from your resume'",
    '        explanations.append(label + ": " + ", ".join(match.canonical for match in preferred_skills[:8]) + ".")',
    '',
    '    if missing_required:',
    '        n = len(missing_required)',
    '        s = "s" if n != 1 else ""',
    "        label = f'{n} required skill{s} not in your resume (listed for review, never auto-inserted)'",
    '        explanations.append(label + ": " + ", ".join(match.term for match in missing_required[:8]) + ".")',
    '',
    '    if missing_preferred:',
    '        n = len(missing_preferred)',
    '        s = "s" if n != 1 else ""',
    "        explanations.append(",
    '            f\'{n} preferred skill{s} not in your resume: \',',
    '            + ", ".join(match.term for match in missing_preferred[:8])',
    '            + ".")',
    '',
]

# Replace lines 352-374 (indices 351-373 inclusive)
# Keep lines before 351 and after 373 (index 373 is line 374, we want to keep from 374 onward)
# Actually lines[351:374] gives indices 351 through 373 (33 lines)
# We want to replace indices 351 through 373 with our new_lines

# But we need to be careful - the original has 352-374 as line numbers
# In 0-indexed: lines 351 to 373 inclusive = 23 lines
# Our new_lines has how many? Let me count...

# Actually, let me just do a simpler approach - replace using string matching
# Find the start marker and end marker

start_marker = 'if required_skills:'
end_marker = '    return TailorAnalysis('

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx >= 0 and end_idx >= 0:
    # Get the section between start and end
    section = content[start_idx:end_idx]
    # Now replace the section with properly formatted version
    # But this is getting complex. Let me just rewrite the whole file section by section.
    
    # Let me take a even simpler approach - just write the entire fixed file
    pass
else:
    print(f"start_idx={start_idx}, end_idx={end_idx}")