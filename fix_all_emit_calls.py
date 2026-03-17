import re

files_to_fix = [
    'tests/test_hook_integration.py',
    'tests/test_hook_realtime.py',
]

for filepath in files_to_fix:
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find all emit_event calls and add validate=False if not present
    # This regex finds emit_event( ... ) patterns
    pattern = r'(emit_event\([^)]*)\)'
    
    def add_validate(match):
        call = match.group(1)
        if 'validate=' not in call:
            return call + ', validate=False)'
        return call + ')'
    
    # Process line by line to handle multi-line calls
    lines = content.split('\n')
    in_emit_call = False
    updated_lines = []
    emit_start = -1
    
    for i, line in enumerate(lines):
        if 'emit_event(' in line and 'validate=' not in line:
            in_emit_call = True
            emit_start = i
        
        if in_emit_call:
            if ')' in line and not line.strip().startswith('#'):
                # End of emit_event call
                # Check if validate is already there
                # Collect all lines from emit_start to here
                call_lines = lines[emit_start:i+1]
                call_text = '\n'.join(call_lines)
                
                if 'validate=' not in call_text:
                    # Add validate=False before the closing paren
                    line = line.rstrip()
                    if line.endswith(')'):
                        line = line[:-1] + ', validate=False)'
                
                in_emit_call = False
        
        updated_lines.append(line)
    
    with open(filepath, 'w') as f:
        f.write('\n'.join(updated_lines))
    
    print(f'Updated {filepath}')
