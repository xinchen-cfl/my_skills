#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


def load_jsonl(path: Path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def dump_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def normalize_text(text: str) -> str:
    text = text or ''
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def canonical_title(title: str) -> str:
    title = normalize_text(title)
    title = re.sub(r'v?\d+(?:\.\d+)+$', '', title, flags=re.I)
    return title.strip()


def deduplicate(rows):
    seen = set()
    out = []
    dup = 0
    for row in rows:
        key_raw = f"{row.get('source_url','')}|{normalize_text(row.get('content',''))}"
        key = hashlib.sha1(key_raw.encode('utf-8')).hexdigest()
        if key in seen:
            dup += 1
            continue
        seen.add(key)
        out.append(row)
    return out, dup


def split_sentences(text: str):
    parts = re.split(r'(?<=[。！？.!?])\s+|\n+', text)
    return [p.strip() for p in parts if p and p.strip()]


def find_heading_sections(text: str):
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    sections = []
    current_title = None
    current_buf = []
    heading_pat = re.compile(r'^(#{1,6}\s+.+|[一二三四五六七八九十]+[、.]?.+|\d+[.)、]\s+.+|[A-Z][A-Za-z0-9 _-]{2,50}:?)$')
    for line in lines:
        if heading_pat.match(line) and len(line) <= 80:
            if current_title and current_buf:
                sections.append({'section_title': current_title, 'section_text': ' '.join(current_buf).strip()})
            current_title = re.sub(r'^(#{1,6}\s*|[一二三四五六七八九十]+[、.]?|\d+[.)、]\s*)', '', line).strip(':： ')
            current_buf = []
        else:
            current_buf.append(line)
    if current_title and current_buf:
        sections.append({'section_title': current_title, 'section_text': ' '.join(current_buf).strip()})
    return [s for s in sections if len(s['section_text']) >= 40]


def sentence_windows(text: str, window_size: int = 3, overlap: int = 1):
    sents = split_sentences(text)
    if not sents:
        return []
    if len(sents) <= window_size:
        return [{'section_title': '正文-1', 'section_text': ' '.join(sents)}]
    sections = []
    step = max(1, window_size - overlap)
    idx = 1
    for start in range(0, len(sents), step):
        chunk = ' '.join(sents[start:start+window_size]).strip()
        if not chunk:
            continue
        if len(chunk) < 80 and sections:
            sections[-1]['section_text'] += ' ' + chunk
            continue
        sections.append({'section_title': f'正文-{idx}', 'section_text': chunk})
        idx += 1
        if start + window_size >= len(sents):
            break
    return sections


def parse_sections(text: str):
    sections = find_heading_sections(text)
    if sections:
        return sections
    return sentence_windows(text)


def quality_score(section_title: str, text: str):
    score = 0
    n = len(text)
    if n >= 120:
        score += 2
    elif n >= 60:
        score += 1
    if not section_title.startswith('正文-1'):
        score += 1
    if re.search(r'\b\d+(?:\.\d+)?\b', text):
        score += 1
    if re.search(r'(warning|risk|注意|风险|步骤|requirement|policy)', text, re.I):
        score += 1
    return score


def low_value(text: str, section_title: str):
    t = text.strip()
    if len(t) < 40:
        return True
    if len(t) < 80 and section_title.startswith('正文-'):
        return True
    if re.fullmatch(r'[A-Za-z0-9 .;:()\-_/]+', t) and len(t) < 120:
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description='通用RAG数据清洗脚本')
    ap.add_argument('--input', required=True)
    ap.add_argument('--output-dir', required=True)
    args = ap.parse_args()

    rows = load_jsonl(Path(args.input))
    rows, dup_count = deduplicate(rows)
    docs = []
    chunks = []

    for row in rows:
        title = row.get('title', '')
        text = normalize_text(row.get('content', ''))
        doc_id = hashlib.sha256(f"{row.get('source_url','')}|{title}|{row.get('effective_date','')}".encode('utf-8')).hexdigest()[:16]
        sections = parse_sections(text)
        doc = {
            'doc_id': doc_id,
            'title': title,
            'source_org': row.get('source_org', 'unknown'),
            'source_url': row.get('source_url', ''),
            'publish_date': row.get('publish_date'),
            'effective_date': row.get('effective_date', datetime.now().strftime('%Y-%m-%d')),
            'crawl_date': row.get('crawl_date'),
            'region': row.get('region', 'LOCAL'),
            'doc_type': row.get('doc_type', 'unknown'),
            'version': row.get('version', 'generic.1'),
            'is_superseded': False,
            'sections': sections,
            'citation_text': text[:240],
        }
        docs.append(doc)
        for idx, sec in enumerate(sections, start=1):
            sec_text = normalize_text(sec['section_text'])
            if low_value(sec_text, sec['section_title']):
                continue
            chunks.append({
                'chunk_id': f'{doc_id}_s{idx}',
                'doc_id': doc_id,
                'title': title,
                'section_title': sec['section_title'],
                'text': sec_text,
                'chunk_order': idx,
                'char_count': len(sec_text),
                'source_url': row.get('source_url', ''),
                'source_org': row.get('source_org', 'unknown'),
                'effective_date': row.get('effective_date', datetime.now().strftime('%Y-%m-%d')),
                'doc_type': row.get('doc_type', 'unknown'),
                'region': row.get('region', 'LOCAL'),
                'quality_score': quality_score(sec['section_title'], sec_text),
                'citation_text': text[:240],
            })

    out_dir = Path(args.output_dir)
    dump_jsonl(out_dir / 'clean_documents.jsonl', docs)
    dump_jsonl(out_dir / 'chunks.jsonl', chunks)
    report = {
        'run_at': datetime.now().isoformat(timespec='seconds'),
        'input_docs': len(rows),
        'deduplicated_docs': len(docs),
        'dropped_duplicates': dup_count,
        'chunk_count': len(chunks),
        'avg_chunks_per_doc': round(len(chunks) / max(1, len(docs)), 2),
    }
    (out_dir / 'cleaning_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
