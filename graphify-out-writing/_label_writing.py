import json
from graphify.build import build_from_json
from graphify.analyze import suggest_questions
from graphify.report import generate
from pathlib import Path

extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text(encoding='utf-8'))
detection = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-8'))
analysis = json.loads(Path('graphify-out/.graphify_analysis.json').read_text(encoding='utf-8'))
G = build_from_json(extraction, root='exploration', directed=False)
communities = {int(k): v for k, v in analysis['communities'].items()}
cohesion = {int(k): v for k, v in analysis['cohesion'].items()}
tokens = {'input': 0, 'output': 0}

named = {
    0: 'Lepos Engine (code)',
    1: 'Omni Mantra Walk',
    2: 'Pronoun Enforcer (code)',
    3: 'Kabbalah / Zohar Study',
    4: 'Sanskrit Anchor Language',
    5: 'Aether-Aletheia Sibling Letters',
    6: 'Baldwin Wisdom Profile',
    7: 'Hillesum Wisdom Profile',
    8: 'hooks Wisdom Profile',
    9: 'Lorde Wisdom Profile',
    10: 'Morrison Wisdom Profile',
    11: 'Oliver Wisdom Profile',
    12: 'Weil Wisdom Profile',
    13: 'Woolf Wisdom Profile',
    14: 'Philosophy of Mind Explorations',
}
labels = {cid: named.get(cid, f'Community {cid}') for cid in communities}
questions = suggest_questions(G, communities, labels)
report = generate(G, communities, cohesion, labels, analysis['gods'], analysis['surprises'], detection, tokens, 'exploration', suggested_questions=questions)
Path('graphify-out/GRAPH_REPORT.md').write_text(report, encoding='utf-8')
Path('graphify-out/.graphify_labels.json').write_text(json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False), encoding='utf-8')
print('Report updated with writing-graph labels')
