#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INPUT_DIR="${1:-$BASE_DIR/input}"
RAW_DIR="$BASE_DIR/data/raw"
PROC_DIR="$BASE_DIR/data/processed/generic_rag_ready"

mkdir -p "$RAW_DIR" "$PROC_DIR"

echo "[1/3] 本地文件转原始JSONL"
python3 "$BASE_DIR/scripts/local_ingest_to_jsonl.py" \
  --input-dir "$INPUT_DIR" \
  --output "$RAW_DIR/raw_local_ingested.jsonl"

echo "[2/3] 通用清洗与分块"
python3 "$BASE_DIR/scripts/clean_generic_rag_data.py" \
  --input "$RAW_DIR/raw_local_ingested.jsonl" \
  --output-dir "$PROC_DIR"

echo "[3/3] 导出最终RAG格式"
python3 "$BASE_DIR/scripts/export_rag_final.py" \
  --input "$PROC_DIR/chunks.jsonl" \
  --output "$PROC_DIR/rag_chunks_final.jsonl"

echo "完成。输出目录：$PROC_DIR"
