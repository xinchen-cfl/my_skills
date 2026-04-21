#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

ALIAS_MAP = {
    "扑热息痛": "对乙酰氨基酚",
    "acetaminophen": "对乙酰氨基酚",
    "paracetamol": "对乙酰氨基酚",
    "ibuprofen": "布洛芬",
    "oseltamivir": "奥司他韦",
}

SECTION_ALIASES = {
    "适应症": ["适应症", "indications and usage", "indications", "purpose"],
    "用法用量": ["用法用量", "dosage and administration", "dosage", "administration"],
    "禁忌": ["禁忌", "contraindications"],
    "不良反应": ["不良反应", "adverse reactions", "side effects", "adverse events"],
    "相互作用": ["相互作用", "drug interactions", "interactions"],
    "警示": ["警示", "warnings", "precautions", "boxed warning"],
    "背景": ["background", "objective", "objectives", "introduction"],
    "方法": ["methods", "method", "patients and methods", "materials and methods"],
    "结果": ["results", "findings"],
    "结论": ["conclusion", "conclusions", "interpretation", "discussion"],
    "摘要": ["brief summary", "abstract", "summary"],
}


def load_jsonl(path: Path) -> List[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def dump_jsonl(path: Path, rows: List[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_drug_tags(tags: List[str]) -> List[str]:
    normalized = []
    for t in tags or []:
        key = t.strip()
        normalized.append(ALIAS_MAP.get(key.lower(), ALIAS_MAP.get(key, key)))
    return sorted(set(normalized))


def normalize_content(text: str) -> str:
    text = text or ""
    text = text.replace("mg·kg-1·d-1", "mg/kg/day").replace("mg每kg每天", "mg/kg/day")
    for k, v in ALIAS_MAP.items():
        text = re.sub(rf"\b{re.escape(k)}\b", v, text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_doc_id(source_url: str, title: str, effective_date: str) -> str:
    raw = f"{source_url}|{title}|{effective_date}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def split_sentences(text: str) -> List[str]:
    if not text:
        return []
    parts = re.split(r"(?<=[。！？.!?])\s+", text)
    cleaned = [p.strip() for p in parts if p and p.strip()]
    return cleaned if cleaned else [text.strip()]


def is_metadata_sentence(sentence: str) -> bool:
    s = sentence.strip()
    lower = s.lower()
    if len(s) <= 120 and ("doi:" in lower or "pmid:" in lower or "online ahead of print" in lower):
        return True
    if len(s) <= 80 and re.search(r"^\d+\.\s*[A-Za-z].*\d{4}", s):
        return True
    if len(s) <= 40 and re.search(r"^[0-9 .;:-]*[A-Za-z][A-Za-z .()/-]*\d{4}", s):
        return True
    return False


def build_sentence_windows(text: str, window_size: int = 3, overlap: int = 1) -> List[dict]:
    sentences = [s for s in split_sentences(text) if not is_metadata_sentence(s)]
    if not sentences:
        return []
    if len(sentences) <= window_size:
        return [{"section_title": "正文-1", "section_text": " ".join(sentences)}]

    sections = []
    step = max(1, window_size - overlap)
    index = 1
    for start in range(0, len(sentences), step):
        chunk_sentences = sentences[start : start + window_size]
        if not chunk_sentences:
            continue
        chunk_text = " ".join(chunk_sentences).strip()
        if len(chunk_text) < 80 and sections:
            sections[-1]["section_text"] += " " + chunk_text
            continue
        sections.append({"section_title": f"正文-{index}", "section_text": chunk_text})
        index += 1
        if start + window_size >= len(sentences):
            break
    return sections


def find_structured_sections(content: str) -> List[dict]:
    matches = []
    for canonical, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            pattern = re.compile(rf"(?i)(?<!\w){re.escape(alias)}\s*[:：]", re.IGNORECASE)
            for m in pattern.finditer(content):
                matches.append((m.start(), m.end(), canonical, alias))
    if not matches:
        return []

    matches.sort(key=lambda x: x[0])
    deduped = []
    used_starts = set()
    for item in matches:
        if item[0] in used_starts:
            continue
        used_starts.add(item[0])
        deduped.append(item)

    sections = []
    for idx, (start, end, canonical, _alias) in enumerate(deduped):
        next_start = deduped[idx + 1][0] if idx + 1 < len(deduped) else len(content)
        section_text = content[end:next_start].strip(" 。;；:\n\t")
        if len(section_text) < 20:
            continue
        sections.append({"section_title": canonical, "section_text": section_text})
    return sections


def parse_sections(content: str) -> List[dict]:
    sections = find_structured_sections(content)
    if sections:
        return sections
    return build_sentence_windows(content, window_size=3, overlap=1)


def deduplicate(rows: List[dict]) -> Tuple[List[dict], int]:
    seen = set()
    out = []
    dup = 0
    for row in rows:
        key_raw = f"{row.get('source_url','')}|{normalize_content(row.get('content',''))}"
        key = hashlib.sha1(key_raw.encode("utf-8")).hexdigest()
        if key in seen:
            dup += 1
            continue
        seen.add(key)
        out.append(row)
    return out, dup


def canonical_title(title: str) -> str:
    title = title or ""
    title = re.sub(r"[（(]\s*\d{4}[^）)]*[）)]", "", title)
    title = re.sub(r"\s+", "", title)
    return title.strip()


def apply_supersede_flag(rows: List[dict]) -> List[dict]:
    grouped: Dict[Tuple[str, str, str], List[dict]] = {}
    for r in rows:
        k = (canonical_title(r.get("title", "")), r.get("source_org", ""), r.get("doc_type", ""))
        grouped.setdefault(k, []).append(r)

    for _, items in grouped.items():
        items.sort(key=lambda x: x.get("effective_date", ""))
        for i, item in enumerate(items):
            item["is_superseded"] = i < len(items) - 1
    return rows


def to_chunk_rows(doc: dict) -> List[dict]:
    chunks = []
    for idx, sec in enumerate(doc["sections"], start=1):
        text = sec["section_text"].strip()
        if not text:
            continue
        chunk_id = f"{doc['doc_id']}_s{idx}"
        chunks.append(
            {
                "chunk_id": chunk_id,
                "doc_id": doc["doc_id"],
                "title": doc["title"],
                "section_title": sec["section_title"],
                "text": text,
                "chunk_order": idx,
                "char_count": len(text),
                "source_url": doc["source_url"],
                "source_org": doc["source_org"],
                "effective_date": doc["effective_date"],
                "is_superseded": doc["is_superseded"],
                "citation_text": doc["citation_text"],
                "doc_type": doc["doc_type"],
                "region": doc["region"],
                "drug_tags": doc["drug_tags"],
                "disease_tags": doc["disease_tags"],
                "population": doc.get("population", []),
                "evidence_level": doc.get("evidence_level"),
                "recommendation_strength": doc.get("recommendation_strength"),
            }
        )
    return chunks


def transform(rows: List[dict]) -> Tuple[List[dict], List[dict], dict]:
    original = len(rows)
    rows, dup_count = deduplicate(rows)

    docs = []
    for r in rows:
        content_norm = normalize_content(r.get("content", ""))
        drug_tags = normalize_drug_tags(r.get("drug_tags", []))
        sections = parse_sections(content_norm)

        doc = {
            "doc_id": build_doc_id(r.get("source_url", ""), r.get("title", ""), r.get("effective_date", "")),
            "title": r.get("title", ""),
            "source_org": r.get("source_org", ""),
            "source_url": r.get("source_url", ""),
            "publish_date": r.get("publish_date"),
            "effective_date": r.get("effective_date", ""),
            "crawl_date": r.get("crawl_date"),
            "region": r.get("region", "CN"),
            "doc_type": r.get("doc_type", "unknown"),
            "drug_tags": drug_tags,
            "disease_tags": sorted(set(r.get("disease_tags", []))),
            "population": sorted(set(r.get("population", []))),
            "evidence_level": r.get("evidence_level"),
            "recommendation_strength": r.get("recommendation_strength"),
            "version": r.get("version", "v1"),
            "is_superseded": False,
            "sections": sections,
            "citation_text": content_norm[:240],
        }
        docs.append(doc)

    docs = apply_supersede_flag(docs)

    chunks = []
    for d in docs:
        chunks.extend(to_chunk_rows(d))

    chunk_lengths = [c["char_count"] for c in chunks]
    report = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "input_docs": original,
        "deduplicated_docs": len(docs),
        "dropped_duplicates": dup_count,
        "chunk_count": len(chunks),
        "avg_chunks_per_doc": round(len(chunks) / max(1, len(docs)), 2),
        "avg_chunk_chars": round(sum(chunk_lengths) / max(1, len(chunk_lengths)), 2),
        "superseded_docs": sum(1 for d in docs if d["is_superseded"]),
        "active_docs": sum(1 for d in docs if not d["is_superseded"]),
    }
    return docs, chunks, report


def main() -> None:
    ap = argparse.ArgumentParser(description="医药RAG清洗脚本（增强版）")
    ap.add_argument("--input", required=True, help="原始JSONL路径")
    ap.add_argument("--output-dir", required=True, help="输出目录")
    args = ap.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = load_jsonl(input_path)
    docs, chunks, report = transform(rows)

    dump_jsonl(out_dir / "clean_documents.jsonl", docs)
    dump_jsonl(out_dir / "chunks.jsonl", chunks)
    (out_dir / "cleaning_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
