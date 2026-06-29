# Composite RAG Corpus

This folder is the staging area for online references used by the Composite AI
assistant. The initial pipeline is intentionally conservative:

- sources must be listed in `online_sources.seed.json`
- source domains must pass an allowlist
- paywalled or rights-managed pages are kept as metadata only
- collected artifacts are written under `online_corpus/`
- every run writes `online_corpus/collection_manifest.json`

Run a metadata-only validation:

```bash
python scripts/rag_collect_online_sources.py --metadata-only
```

Collect downloadable sources:

```bash
python scripts/rag_collect_online_sources.py
```

PDF text extraction uses `pypdf` when installed. Without it, the raw PDF is
extracted with the local `pdftotext` command when available. If neither is
available, the raw PDF is saved and marked `raw_only` in the manifest.

Build the local knowledge index from online chunks plus internal DD Laminate
materials:

```bash
python scripts/rag_build_knowledge_index.py
```

The generated index is written to:

```text
data/rag/knowledge_index.json
```

Query the local index from the command line:

```bash
python scripts/rag_query_index.py "Double-Double laminate Pt" --top-k 5
```

Ask the grounded assistant from the command line:

```bash
python scripts/rag_answer.py "A12 membrane coupling은 왜 중요해?" --top-k 5
```

The standalone DD server also exposes a retrieval endpoint once the index
exists:

```text
GET /api/v1/rag/search?q=Double-Double%20laminate%20Pt&top_k=5
```

It also exposes a grounded answer endpoint:

```text
POST /api/v1/rag/answer
```

Example body:

```json
{
  "query": "A12 membrane coupling은 왜 중요해?",
  "top_k": 5,
  "use_llm": true,
  "language": "ko"
}
```

This first index uses deterministic local TF-IDF style sparse vectors so it can
run on a new machine without API keys. The source/chunk format is explicit so a
managed embedding backend can be added later.

When `OPENAI_API_KEY` is configured, `/api/v1/rag/answer` calls the OpenAI
Responses API using `OPENAI_RAG_MODEL` or the default `gpt-5.4-mini`. If no key
is configured or the model call fails, the endpoint returns a local extractive
answer with citations.

Example local start with LLM synthesis enabled:

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_RAG_MODEL="gpt-5.4-mini"
.venv/bin/python -m uvicorn src.backend.dd_laminate_app:app --host 0.0.0.0 --port 8000
```

For Cloudflare/public serving, set the same environment variables in the
process that starts the DD Laminate server. The web checkbox only requests LLM
mode; the backend still falls back safely when the API key is not present.
