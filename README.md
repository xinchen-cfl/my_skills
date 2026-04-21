# hermes-rag-cleaning-skills

可迁移的 Hermes skills 仓库，包含：

- medical-rag-data-cleaning：医学/药学 RAG 数据清洗
- generic-rag-data-cleaning：通用 RAG 数据清洗

目录结构：

```text
skills/
  data-science/
    medical-rag-data-cleaning/
    generic-rag-data-cleaning/
```

使用方式：
1. 将对应 skill 目录复制到目标机器的 `~/.hermes/skills/data-science/`
2. 或直接把 `scripts/` 目录下脚本拿出来单独运行

说明：
- 这两个 skill 都支持本地文件输入
- 不依赖外部 API 也可完成清洗与导出
