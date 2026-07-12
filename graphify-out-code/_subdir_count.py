import json
from collections import Counter

d = json.load(open('graphify-out/.graphify_detect.json', encoding='utf-8'))
scan_root = d.get('scan_root', '').replace('\\', '/')
files_by_type = d.get('files', {})
all_files = []
for k in ('code', 'document', 'paper', 'image', 'video'):
    for f in files_by_type.get(k, []):
        all_files.append(f.replace('\\', '/'))

excl_prefix = scan_root + '/graphify-out/'
counter = Counter()
for f in all_files:
    if f.startswith(excl_prefix):
        continue
    rel = f[len(scan_root) + 1:] if f.startswith(scan_root + '/') else f
    parts = rel.split('/', 1)
    top = parts[0] if len(parts) > 1 else '(root)'
    counter[top] += 1

print('scan_root:', scan_root)
print('top-level subdirectories by file count:')
for name, cnt in counter.most_common(12):
    print(f'  {name}: {cnt}')
