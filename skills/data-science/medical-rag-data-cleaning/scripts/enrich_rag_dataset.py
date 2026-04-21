#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter
from pathlib import Path

DRUG_KEYWORDS = {
    "对乙酰氨基酚": ["对乙酰氨基酚", "acetaminophen", "paracetamol"],
    "布洛芬": ["布洛芬", "ibuprofen"],
    "奥司他韦": ["奥司他韦", "oseltamivir"],
}

POPULATION_PATTERNS = {
    "儿童": [r"儿童", r"pediatric", r"children"],
    "成人": [r"成人", r"adult", r"adults"],
    "孕妇": [r"孕", r"pregnan"],
    "老年人": [r"老年", r"elderly", r"older adults"],
}

RISK_PATTERNS = [r"禁忌", r"contraindicat", r"warning", r"precaution", r"severe", r"serious", r"liver damage", r"allergy"]
DOSAGE_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s?(?:mg|g|ml|mg/kg/day|mcg)\b", re.I)


def load_jsonl(path: Path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def dump_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


TOPIC_PATTERNS = {
    '对乙酰氨基酚': [r'对乙酰氨基酚', r'acetaminophen', r'paracetamol'],
    '布洛芬': [r'布洛芬', r'ibuprofen'],
    '奥司他韦': [r'奥司他韦', r'oseltamivir'],
    '发热': [r'发热', r'fever', r'antipyretic'],
    '疼痛': [r'疼痛', r'pain', r'analgesic'],
    '流感': [r'流感', r'influenza', r'flu'],
}


def topic_focus_score(title: str, text: str, doc_type: str) -> int:
    score = 0
    combo = f"{title} {text}"
    lower = combo.lower()
    title_lower = title.lower()
    drug_hits = 0
    topic_hits = 0
    drug_title_hits = 0
    drug_patterns = list(TOPIC_PATTERNS.items())[:3]
    for key, patterns in TOPIC_PATTERNS.items():
        matched = any(re.search(p, lower, re.I) for p in patterns)
        if matched:
            if key in {'对乙酰氨基酚', '布洛芬', '奥司他韦'}:
                drug_hits += 1
            else:
                topic_hits += 1
    for _drug, patterns in drug_patterns:
        if any(re.search(p, title_lower, re.I) for p in patterns):
            drug_title_hits += 1
            score += 2
    drug_mention_count = sum(len(re.findall(p, lower, re.I)) for _drug, patterns in drug_patterns for p in patterns)
    if drug_hits >= 1:
        score += 1
    if drug_mention_count >= 3:
        score += 1
    if topic_hits >= 1:
        score += 1
    if doc_type in {'label', 'rct'} and drug_hits >= 1:
        score += 1
    if drug_title_hits == 0 and drug_mention_count < 2:
        score = min(score, 1)
    return score


def infer_evidence_type(doc_type: str, title: str, text: str) -> str:
    lower = f"{title} {text}".lower()
    if doc_type == 'label':
        return 'regulatory_label'
    if doc_type == 'rct':
        return 'clinical_trial_registry'
    if 'systematic review' in lower or 'meta-analysis' in lower:
        return 'systematic_review'
    if 'randomized' in lower or 'placebo-controlled' in lower:
        return 'randomized_trial'
    if doc_type == 'paper':
        return 'research_paper'
    return 'other'


def infer_study_design(title: str, text: str) -> str | None:
    lower = f"{title} {text}".lower()
    if 'systematic review' in lower:
        return 'systematic_review'
    if 'meta-analysis' in lower:
        return 'meta_analysis'
    if 'randomized' in lower:
        return 'randomized_trial'
    if 'retrospective' in lower:
        return 'retrospective_study'
    if 'cohort' in lower:
        return 'cohort_study'
    if 'case report' in lower:
        return 'case_report'
    return None


def extract_drugs(text: str, existing: list[str]):
    found = set(existing or [])
    lower = text.lower()
    for canonical, words in DRUG_KEYWORDS.items():
        if any(w.lower() in lower for w in words):
            found.add(canonical)
    return sorted(found)


def extract_population(text: str, existing: list[str]):
    found = set(existing or [])
    for canonical, pats in POPULATION_PATTERNS.items():
        if any(re.search(p, text, re.I) for p in pats):
            found.add(canonical)
    return sorted(found)


def trial_status(text: str):
    m = re.search(r"试验状态[:：]\s*([A-Z_]+)", text)
    return m.group(1) if m else None


def quality_score(chunk: dict) -> int:
    score = 0
    text = chunk['text']
    if chunk['char_count'] >= 120:
        score += 2
    elif chunk['char_count'] >= 60:
        score += 1
    if chunk['section_title'] not in {'正文-1'}:
        score += 1
    if DOSAGE_PATTERN.search(text):
        score += 1
    if any(re.search(p, text, re.I) for p in RISK_PATTERNS):
        score += 1
    if infer_study_design(chunk['title'], text):
        score += 1
    return score


def low_value(chunk: dict) -> bool:
    text = chunk['text'].strip()
    if chunk['char_count'] < 40:
        return True
    if len(text) < 80 and chunk['section_title'].startswith('正文-'):
        return True
    if re.fullmatch(r"[A-Za-z0-9 .;:()\-_/]+", text) and len(text) < 120:
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description='增强RAG数据集并过滤低价值chunk')
    ap.add_argument('--docs', required=True)
    ap.add_argument('--chunks', required=True)
    ap.add_argument('--output-dir', required=True)
    args = ap.parse_args()

    docs = load_jsonl(Path(args.docs))
    chunks = load_jsonl(Path(args.chunks))

    enriched_docs = []
    kept_doc_ids = set()
    dropped_docs = 0
    for d in docs:
        doc_text = ' '.join(sec['section_text'] for sec in d.get('sections', []))
        d['drug_tags'] = extract_drugs(doc_text, d.get('drug_tags', []))
        d['population'] = extract_population(doc_text, d.get('population', []))
        d['evidence_type'] = infer_evidence_type(d.get('doc_type', ''), d.get('title', ''), doc_text)
        d['study_design'] = infer_study_design(d.get('title', ''), doc_text)
        d['topic_focus_score'] = topic_focus_score(d.get('title', ''), doc_text, d.get('doc_type', ''))
        if d['topic_focus_score'] < 2:
            dropped_docs += 1
            continue
        enriched_docs.append(d)
        kept_doc_ids.add(d['doc_id'])

    filtered_chunks = []
    dropped = 0
    section_counter = Counter()
    evidence_counter = Counter()
    for c in chunks:
        if c['doc_id'] not in kept_doc_ids:
            dropped += 1
            continue
        if low_value(c):
            dropped += 1
            continue
        text = c['text']
        c['drug_tags'] = extract_drugs(text, c.get('drug_tags', []))
        c['population'] = extract_population(text, c.get('population', []))
        c['dosage_mentions'] = DOSAGE_PATTERN.findall(text)[:10]
        c['risk_flags'] = sorted(set(m.group(0).lower() for p in RISK_PATTERNS for m in re.finditer(p, text, re.I)))
        c['trial_status'] = trial_status(text)
        c['evidence_type'] = infer_evidence_type(c.get('doc_type', ''), c.get('title', ''), text)
        c['study_design'] = infer_study_design(c.get('title', ''), text)
        c['topic_focus_score'] = topic_focus_score(c.get('title', ''), text, c.get('doc_type', ''))
        c['quality_score'] = quality_score(c)
        c['is_rag_candidate'] = c['quality_score'] >= 2 and c['topic_focus_score'] >= 2
        if not c['is_rag_candidate']:
            dropped += 1
            continue
        filtered_chunks.append(c)
        section_counter[c['section_title']] += 1
        evidence_counter[c['evidence_type']] += 1

    out_dir = Path(args.output_dir)
    dump_jsonl(out_dir / 'enriched_documents.jsonl', enriched_docs)
    dump_jsonl(out_dir / 'rag_chunks.jsonl', filtered_chunks)

    report = {
        'input_docs': len(docs),
        'input_chunks': len(chunks),
        'output_docs': len(enriched_docs),
        'output_chunks': len(filtered_chunks),
        'dropped_low_value_or_unfocused_docs': dropped_docs,
        'dropped_low_value_or_unfocused_chunks': dropped,
        'avg_quality_score': round(sum(c['quality_score'] for c in filtered_chunks) / max(1, len(filtered_chunks)), 2),
        'avg_topic_focus_score': round(sum(c['topic_focus_score'] for c in filtered_chunks) / max(1, len(filtered_chunks)), 2),
        'rag_candidate_chunks': sum(1 for c in filtered_chunks if c['is_rag_candidate']),
        'section_distribution_top': dict(section_counter.most_common(12)),
        'evidence_type_distribution': dict(evidence_counter.most_common()),
    }
    (out_dir / 'rag_readiness_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
