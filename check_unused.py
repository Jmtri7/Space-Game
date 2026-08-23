import re

files = ['screens.py', 'ship.py', 'objects.py', 'utils.py']
unused = []

for fname in files:
    with open(fname) as f:
        content = f.read()
    
    # Find all method definitions
    methods = re.findall(r'    def (\w+)\(', content)
    
    for method in methods:
        # Skip special methods and common ones
        if method.startswith('__') or method in ['handle_input', 'update', 'draw', 'get_state', 'restore_state']:
            continue
        
        # Check if called (beyond the definition)
        lines = content.split('\n')
        def_line = next(i for i, l in enumerate(lines) if f'def {method}(' in l)
        remaining = '\n'.join(lines[def_line+1:])
        
        if f'{method}(' not in remaining and f'.{method}(' not in remaining:
            unused.append((fname, method))

print("Potentially unused methods:")
for fname, method in unused:
    print(f"  {fname}: {method}()")
