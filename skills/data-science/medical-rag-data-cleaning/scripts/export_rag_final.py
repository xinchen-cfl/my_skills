#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def load_jsonl(path: Path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def main():
    ap = argparse.ArgumentParser(description='导出最终RAG接入JSONL')
    ap.add_argument('--input', required=True, help='增强后的rag_chunks.jsonl')
    ap.add_argument('--output', required=True, help='最终输出 rag_chunks_final.jsonl')
    args = ap.parse_args()

    src = Path(args.input)
    out = Path(args.output)
    rows = []
    for r in load_jsonl(src):
        rows.append({
            'id': r['chunk_id'],
            'text': r['text'],
            'title': r['title'],
            'section_title': r['section_title'],
            'source_url': r['source_url'],
            'source_org': r['source_org'],
            'doc_type': r['doc_type'],
            'evidence_type': r['evidence_type'],
            'metadata': {
                'doc_id': r['doc_id'],
                'chunk_order': r['chunk_order'],
                'effective_date': r['effective_date'],
                'region': r['region'],
                'drug_tags': r.get('drug_tags', []),
                'disease_tags': r.get('disease_tags', []),
                'population': r.get('population', []),
                'dosage_mentions': r.get('dosage_mentions', []),
                'risk_flags': r.get('risk_flags', []),
                'trial_status': r.get('trial_status'),
                'study_design': r.get('study_design'),
                'quality_score': r.get('quality_score', 0),
                'topic_focus_score': r.get('topic_focus_score', 0),
                'is_superseded': r.get('is_superseded', False),
                'citation_text': r.get('citation_text', ''),
            }
        })

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(json.dumps(x, ensure_ascii=False) for x in rows) + '\n', encoding='utf-8')
    print(json.dumps({'rows': len(rows), 'output': str(out)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
