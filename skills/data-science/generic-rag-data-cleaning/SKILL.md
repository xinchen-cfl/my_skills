---
name: generic-rag-data-cleaning
description: Use when converting local documents from any domain into a clean, deduplicated, section-aware RAG dataset with JSONL outputs and no external API dependency.
---

# Generic RAG Data Cleaning

## Overview

Turn mixed local documents into a domain-agnostic RAG dataset.

Core principle: standardize first, chunk second, filter noise before retrieval.

## When to Use

Use when:
- You have local files from any domain
- You need a reusable RAG preprocessing workflow
- You want to avoid external APIs
- You need a generic alternative to domain-specific cleaning skills

Use the medical-specific skill instead when:
- You need drug alias normalization
- You need dosage / risk / population extraction
- You need medical section semantics

## Supported Inputs

- `.txt`
- `.md`
- `.html` / `.htm`
- `.json`
- `.jsonl`

## Workflow

### 一键跑完整流程（推荐）

```bash
bash scripts/run_generic_cleaning_pipeline.sh [input目录]
```

如果不传目录，默认使用项目下的 `input/`。

### Step 1: Ingest local files

```bash
python3 scripts/local_ingest_to_jsonl.py \
  --input-dir input \
  --output data/raw/raw_local_ingested.jsonl
```

### Step 2: Clean, deduplicate, and chunk

```bash
python3 scripts/clean_generic_rag_data.py \
  --input data/raw/raw_local_ingested.jsonl \
  --output-dir data/processed/rag_ready_stage1
```

### Step 3: Export final RAG schema

```bash
python3 scripts/export_rag_final.py \
  --input data/processed/rag_ready_stage1/chunks.jsonl \
  --output data/processed/rag_ready_stage1/rag_chunks_final.jsonl
```

## What It Does

- local file ingestion
- basic text normalization
- exact deduplication
- heading-aware section splitting
- sentence-window fallback chunking
- low-value chunk filtering
- unified final JSONL export

## Outputs

- `data/raw/raw_local_ingested.jsonl`
- `data/processed/rag_ready_stage1/clean_documents.jsonl`
- `data/processed/rag_ready_stage1/chunks.jsonl`
- `data/processed/rag_ready_stage1/rag_chunks_final.jsonl`

## Final Chunk Fields

- `id`
- `text`
- `title`
- `section_title`
- `source_url`
- `source_org`
- `doc_type`
- `metadata.doc_id`
- `metadata.chunk_order`
- `metadata.effective_date`
- `metadata.region`
- `metadata.quality_score`
- `metadata.citation_text`

## Common Mistakes

- Embedding whole documents instead of chunks
- Leaving HTML tags uncleaned before chunking
- Keeping very short metadata fragments in retrieval
- Using the generic skill when a domain-specific skill is needed

## Verification

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path('data/processed/rag_ready_stage1/rag_chunks_final.jsonl')
rows = [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
print('chunks=', len(rows))
print('sample=', rows[0]['title'])
PY
```

Expected: chunk count > 0 and valid JSONL rows.

## Supporting Scripts

- `scripts/local_ingest_to_jsonl.py`
- `scripts/clean_generic_rag_data.py`
- `scripts/export_rag_final.py`
- `scripts/run_generic_cleaning_pipeline.sh`
