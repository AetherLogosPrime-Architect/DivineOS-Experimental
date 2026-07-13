from pathlib import Path
import glob, os

# remove old chunk files
for old in glob.glob('graphify-out/.graphify_chunk_files_*.txt'):
    os.remove(old)

files = Path('graphify-out/.graphify_uncached.txt').read_text(encoding='utf-8').strip().split('\n')
# sort by path so same-dir files land together in same chunk
files.sort()

CHUNK_SIZE = 24
chunks = [files[i:i + CHUNK_SIZE] for i in range(0, len(files), CHUNK_SIZE)]

print(f'{len(chunks)} chunks; sizes = {[len(c) for c in chunks]}')
for i, ch in enumerate(chunks, 1):
    Path(f'graphify-out/.graphify_chunk_files_{i:02d}.txt').write_text('\n'.join(ch), encoding='utf-8')
