"""Clean the SHL catalog JSON file."""

import json

catalog_path = 'data/shl_product_catalog.json'

print("Attempting to clean JSON file...")

# Read the file
with open(catalog_path, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Fix: escape literal newlines, tabs, and carriage returns inside strings
def fix_json_strings(text):
    """Escape control characters that are literal in JSON strings."""
    result = []
    in_string = False
    i = 0
    
    while i < len(text):
        char = text[i]
        
        if char == '"' and (i == 0 or text[i-1] != '\\'):
            # Toggle in_string state (not escaped quote)
            in_string = not in_string
            result.append(char)
        elif in_string:
            # We're inside a string
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            elif ord(char) < 32:
                # Other control characters - skip them
                pass
            else:
                result.append(char)
        else:
            # Outside strings
            result.append(char)
        
        i += 1
    
    return ''.join(result)

fixed = fix_json_strings(text)

# Try to parse
try:
    data = json.loads(fixed)
    print(f'Successfully loaded {len(data)} assessments')
    
    # Write the clean version
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print('Cleaned file written successfully')
except json.JSONDecodeError as e:
    print(f'JSON parse error: {e}')
    print(f'Line: {e.lineno}, Column: {e.colno}')
except Exception as e:
    print(f'Error: {e}')

