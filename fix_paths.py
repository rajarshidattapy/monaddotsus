import re

file_path = '/Users/vidipghosh/Desktop/monaddotsus/game.py'
with open(file_path, 'r') as f:
    content = f.read()

# Replace backslashes with forward slashes in strings starting with Assets
def replace_path(match):
    return match.group(0).replace('\\', '/')

# Find strings starting with Assets and containing backslashes
new_content = re.sub(r'["\']Assets\\[^"\']+["\']', replace_path, content)

with open(file_path, 'w') as f:
    f.write(new_content)
