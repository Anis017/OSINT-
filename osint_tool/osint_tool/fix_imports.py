import os
import re

def get_module_names(directory):
    """Return set of .py filenames (without extension) in the directory."""
    modules = set()
    for f in os.listdir(directory):
        if f.endswith('.py') and f != '__init__.py':
            modules.add(f[:-3])  # remove .py
    return modules

def fix_imports_in_file(filepath, module_names):
    """Replace absolute local imports with relative imports in the file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        # Match patterns: from module import ...   or   import module
        # But skip lines that already start with 'from .' or 'import .' (already relative)
        if line.strip().startswith('from .') or line.strip().startswith('import .'):
            new_lines.append(line)
            continue

        # Match 'from module import ...' where module is in module_names
        match_from = re.match(r'^from\s+(\w+)\s+import', line)
        if match_from:
            module = match_from.group(1)
            if module in module_names:
                # Replace with relative import
                new_line = re.sub(r'^from\s+(\w+)\s+import', r'from .\1 import', line)
                new_lines.append(new_line)
                continue

        # Match 'import module' (maybe with multiple modules, but we only change single ones)
        match_import = re.match(r'^import\s+(\w+)$', line.strip())
        if match_import:
            module = match_import.group(1)
            if module in module_names:
                new_line = re.sub(r'^import\s+(\w+)$', r'import .\1', line)
                new_lines.append(new_line)
                continue

        # Keep the line as is
        new_lines.append(line)

    # Write back only if changes were made
    if new_lines != lines:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"Updated: {filepath}")

def main():
    modules_dir = 'modules'
    if not os.path.isdir(modules_dir):
        print(f"Directory '{modules_dir}' not found.")
        return

    module_names = get_module_names(modules_dir)
    print(f"Found modules: {module_names}")

    for filename in os.listdir(modules_dir):
        if filename.endswith('.py'):
            filepath = os.path.join(modules_dir, filename)
            fix_imports_in_file(filepath, module_names)

if __name__ == '__main__':
    main()