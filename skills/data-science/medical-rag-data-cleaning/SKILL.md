---
name: medical-rag-data-cleaning
description: Use when building a medical or pharmaceutical RAG knowledge base from local files or raw documents that need section-aware cleaning, deduplication, metadata enrichment, and RAG-ready JSONL output without relying on external APIs.
---

# Medical RAG Data Cleaning

## Overview

Turn messy medical/pharma source files into a RAG-ready dataset with stable JSONL outputs.

Core principle: keep provenance, clean aggressively, and only send focused chunks into retrieval.

## When to Use

Use when:
- You have local `.txt/.md/.html/.json/.jsonl` source files
- You need a medical/pharma external knowledge base for RAG
- You want deduplication, section-aware chunking, and metadata enrichment
- You cannot or do not want to rely on external APIs

Do not use when:
- You only need one-off document reading
- You need clinical-grade decision support without human review
- Your sources are only scanned PDFs/images and you have no OCR step yet

## Outputs

This skill produces 3 layers:
1. Raw ingestion layer: `raw_local_ingested.jsonl`
2. Clean chunk layer: `chunks.jsonl`
3. Final RAG layer: `rag_chunks_final.jsonl`

## File Layout

Recommended project layout:

```text
project/
  input/                     # local source files
  data/raw/
  data/processed/
  scripts/
```

## Local-only Workflow

### Step 1: Ingest local files into raw JSONL

Supported input types:
- `.txt`
- `.md`
- `.html`
- `.json`
- `.jsonl`

Run:

```bash
python3 scripts/local_ingest_to_jsonl.py \
  --input-dir input \
  --output data/raw/raw_local_ingested.jsonl
```

### Step 2: Clean and section-chunk medical text

Run:

```bash
python3 scripts/clean_medical_data.py \
  --input data/raw/raw_local_ingested.jsonl \
  --output-dir data/processed/rag_ready_stage1
```

### Step 3: Enrich metadata and filter low-value chunks

Run:

```bash
python3 scripts/enrich_rag_dataset.py \
  --docs data/processed/rag_ready_stage1/clean_documents.jsonl \
  --chunks data/processed/rag_ready_stage1/chunks.jsonl \
  --output-dir data/processed/rag_final
```

### Step 4: Convert to final RAG schema

Run:

```bash
python3 scripts/export_rag_final.py \
  --input data/processed/rag_final/rag_chunks.jsonl \
  --output data/processed/rag_final/rag_chunks_final.jsonl
```

## Final Schema

Each final chunk contains:
- `id`
- `text`
- `title`
- `section_title`
- `source_url`
- `source_org`
- `doc_type`
- `evidence_type`
- `metadata.doc_id`
- `metadata.chunk_order`
- `metadata.effective_date`
- `metadata.region`
- `metadata.drug_tags`
- `metadata.disease_tags`
- `metadata.population`
- `metadata.dosage_mentions`
- `metadata.risk_flags`
- `metadata.trial_status`
- `metadata.study_design`
- `metadata.quality_score`
- `metadata.topic_focus_score`
- `metadata.is_superseded`
- `metadata.citation_text`

## Retrieval Guidance

Recommended ranking priority:
1. `regulatory_label`
2. `clinical_trial_registry`
3. `research_paper`

Recommended filtering before retrieval:
- `drug_tags`
- `population`
- `doc_type`
- `region`
- `is_superseded=false`

## Common Mistakes

- Ingesting local files but dropping file path provenance
- Sending whole documents into embeddings instead of chunks
- Mixing low-value metadata snippets into the retrieval set
- Treating first-pass medical RAG as clinical decision automation
- Ignoring `source_url` and `citation_text` in final answers

## Verification

After running the workflow, verify:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path('data/processed/rag_final/rag_chunks_final.jsonl')
rows = [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
print('chunks=', len(rows))
print('sample_keys=', sorted(rows[0].keys()))
print('sample_metadata_keys=', sorted(rows[0]['metadata'].keys()))
PY
```

Expected:
- chunk count > 0
- every row has `id`, `text`, `source_url`, `metadata`

## Supporting Scripts

Load these linked files from the skill when needed:
- `scripts/local_ingest_to_jsonl.py`
- `scripts/clean_medical_data.py`
- `scripts/enrich_rag_dataset.py`
- `scripts/export_rag_final.py`

## Safety Boundary

This skill prepares RAG data. It does NOT certify medical correctness for autonomous treatment advice.
