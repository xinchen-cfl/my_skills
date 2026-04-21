#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime
from html import unescape
from pathlib import Path


SUPPORTED = {'.txt', '.md', '.html', '.htm', '.json', '.jsonl'}


def strip_html(text: str) -> str:
    text = re.sub(r'<script[\s\S]*?</script>', ' ', text, flags=re.I)
    text = re.sub(r'<style[\s\S]*?</style>', ' ', text, flags=re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def guess_doc_type(name: str, text: str) -> str:
    combo = f"{name} {text[:1000]}".lower()
    if any(k in combo for k in ['guideline', '指导原则', '指南', '共识']):
        return 'guideline'
    if any(k in combo for k in ['label', '说明书', 'dosage and administration', 'contraindications']):
        return 'label'
    if any(k in combo for k in ['trial', 'nct', 'clinical study', '随机', '试验']):
        return 'rct'
    if any(k in combo for k in ['review', 'meta-analysis', 'systematic review', 'paper', 'journal']):
        return 'paper'
    return 'unknown'


def normalize_text(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    raw = path.read_text(encoding='utf-8', errors='ignore')
    rows = []
    if suffix in {'.txt', '.md'}:
        rows.append({'title': path.stem, 'content': raw})
    elif suffix in {'.html', '.htm'}:
        title_match = re.search(r'<title[^>]*>(.*?)</title>', raw, flags=re.I | re.S)
        title = strip_html(title_match.group(1)) if title_match else path.stem
        rows.append({'title': title or path.stem, 'content': strip_html(raw)})
    elif suffix == '.jsonl':
        for line in raw.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            rows.append({'title': obj.get('title', path.stem), 'content': obj.get('content') or obj.get('text') or json.dumps(obj, ensure_ascii=False)})
    elif suffix == '.json':
        obj = json.loads(raw)
        if isinstance(obj, list):
            for item in obj:
                rows.append({'title': item.get('title', path.stem) if isinstance(item, dict) else path.stem, 'content': item.get('content') if isinstance(item, dict) else str(item)})
        elif isinstance(obj, dict):
            rows.append({'title': obj.get('title', path.stem), 'content': obj.get('content') or obj.get('text') or json.dumps(obj, ensure_ascii=False)})
        else:
            rows.append({'title': path.stem, 'content': str(obj)})
    return rows


def main():
    ap = argparse.ArgumentParser(description='将本地文档目录转为医药RAG原始JSONL')
    ap.add_argument('--input-dir', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--source-org', default='local_files')
    ap.add_argument('--region', default='LOCAL')
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    output = Path(args.output)
    rows = []
    crawl_date = datetime.now().strftime('%Y-%m-%d')

    for path in sorted(input_dir.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            continue
        try:
            docs = normalize_text(path)
        except Exception:
            continue
        for doc in docs:
            text = re.sub(r'\s+', ' ', (doc.get('content') or '')).strip()
            if len(text) < 40:
                continue
            rows.append({
                'title': doc.get('title') or path.stem,
                'source_org': args.source_org,
                'source_url': str(path.resolve()),
                'publish_date': None,
                'effective_date': crawl_date,
                'crawl_date': crawl_date,
                'region': args.region,
                'doc_type': guess_doc_type(path.name, text),
                'drug_tags': [],
                'disease_tags': [],
                'population': [],
                'evidence_level': None,
                'recommendation_strength': None,
                'version': 'local.1',
                'content': text[:40000],
            })

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + ('\n' if rows else ''), encoding='utf-8')
    print(json.dumps({'output': str(output), 'rows': len(rows)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
