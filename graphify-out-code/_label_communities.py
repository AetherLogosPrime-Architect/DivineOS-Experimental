import json
from graphify.build import build_from_json
from graphify.analyze import suggest_questions
from graphify.report import generate
from pathlib import Path

extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text(encoding='utf-8'))
detection = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-8'))
analysis = json.loads(Path('graphify-out/.graphify_analysis.json').read_text(encoding='utf-8'))
G = build_from_json(extraction, root='src', directed=False)
communities = {int(k): v for k, v in analysis['communities'].items()}
cohesion = {int(k): v for k, v in analysis['cohesion'].items()}
tokens = {'input': 0, 'output': 0}

named = {
    0: 'CLI Wrappers & Constants',
    1: 'Knowledge Engine CLI',
    2: 'Pipeline Gates',
    3: 'Compass & Anti-Substitution',
    4: 'Council Wisdom Profiles',
    5: 'HUD & Goal Commands',
    6: 'Council Consultation Tracking',
    7: 'Clarity System',
    8: 'CLI Enforcement Layer',
    9: 'Engagement Gate & Features',
    10: 'Analysis Commands',
    11: 'Pipeline Phases & Lessons',
    12: 'Session Tracker',
    13: 'RT Protocol & Handoff',
    14: 'Session Feature Detection',
    15: 'Outcome Measurement',
    16: 'Family Member Substrate',
    17: 'Moral Compass Engine',
    18: 'Error Handling',
    19: 'Council Required Gate',
}
labels = {cid: named.get(cid, f'Community {cid}') for cid in communities}
questions = suggest_questions(G, communities, labels)
report = generate(G, communities, cohesion, labels, analysis['gods'], analysis['surprises'], detection, tokens, 'src', suggested_questions=questions)
Path('graphify-out/GRAPH_REPORT.md').write_text(report, encoding='utf-8')
Path('graphify-out/.graphify_labels.json').write_text(json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False), encoding='utf-8')
print('Report updated with labels')
