#!/usr/bin/env python3
"""
assemble_notebook.py
Assembles deep_notes_knowledge_graph.ipynb from cell source files.
Run: python notebook/assemble_notebook.py
"""

import json
import uuid
from pathlib import Path

try:
    import nbformat
    USE_NBFORMAT = True
except ImportError:
    USE_NBFORMAT = False

CELLS_DIR   = Path(__file__).parent / "cells"
OUTPUT_PATH = Path(__file__).parent / "deep_notes_knowledge_graph.ipynb"

# ─── Cell 1: Markdown overview (inline since it's pure markdown) ────────────

CELL_1_MD = """# 🧠 Deep Notes AI
## YouTube Knowledge Extraction & Knowledge Graph Platform

A **14-phase LangGraph pipeline** that transforms raw YouTube videos into a structured, queryable personal knowledge base.

---

### System Architecture

```
YouTube URLs
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                  LangGraph StateGraph                   │
│                                                         │
│  url_processor → transcript_extractor → note_generator │
│       │                                       │         │
│  [Validation]                         [GPT-4o-mini]    │
│                                               │         │
│  topic_extractor → topic_mapper → topic_canonicalizer  │
│  [GPT-4o-mini]      [SQLite]    [Embed+LLM dedup]     │
│                                               │         │
│  graph_writer → topic_aggregator → summary_generator  │
│  [Neo4j/SQLite]    [GPT-4o]        [GPT-4o-mini]      │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────┐
│              Storage Trinity                  │
│  SQLite (source) | Neo4j (graph) | Qdrant    │
└──────────────────────────────────────────────┘
    │
    ▼
query_video() | query_topic() | query_topic_summary()
```

### Technology Stack
| Component | Technology | Reason |
|-----------|-----------|--------|
| Orchestration | LangGraph 0.2+ | Production-grade stateful agent graphs |
| LLM Extraction | GPT-4o-mini | Cheap, fast, reliable JSON output |
| LLM Reasoning | GPT-4o | High-quality consolidation & aggregation |
| Embeddings | text-embedding-3-small | Best cost/quality for semantic search |
| Transcripts | youtube-transcript-api | No auth required |
| Schemas | Pydantic v2 | Type-safe, validated data models |
| Retry Logic | Tenacity | Exponential backoff for all API calls |
| Graph DB | Neo4j (optional) | Cypher traversal for topic relationships |
| Vector DB | Qdrant (in-memory) | Zero-infra semantic search |
| SQL DB | SQLite | Zero-infra source of truth, PostgreSQL-ready |

### Quick Start
1. **Run cells 1-12** to initialise all infrastructure (one-time setup)
2. **Edit Cell 22** to add your YouTube URLs
3. **Run cells 13-22** to execute the full pipeline
4. **Run Cell 23** to explore your knowledge base
"""

# ─── Ordered cell source files ──────────────────────────────────────────────

CELL_FILES = [
    ("cell_02_install.py",   "code"),
    ("cell_03_imports.py",   "code"),
    ("cell_04_config.py",    "code"),
    ("cell_05_schemas.py",   "code"),
    ("cell_06_sqlite.py",    "code"),
    ("cell_07_neo4j.py",     "code"),
    ("cell_08_qdrant.py",    "code"),
    ("cell_09_utils.py",     "code"),
    ("cell_10_middleware.py","code"),
    ("cell_11_prompts.py",   "code"),
    ("cell_12_llm.py",       "code"),
    ("cell_13_phase1.py",    "code"),
    ("cell_14_phase2.py",    "code"),
    ("cell_15_phase34.py",   "code"),
    ("cell_16_phase5.py",    "code"),
    ("cell_17_phase6.py",    "code"),
    ("cell_18_phase7.py",    "code"),
    ("cell_19_phase8.py",    "code"),
    ("cell_20_graph.py",     "code"),
    ("cell_21_query.py",     "code"),
    ("cell_22_demo.py",      "code"),
    ("cell_23_queries.py",   "code"),
]


def make_uid() -> str:
    return str(uuid.uuid4()).replace("-", "")[:8]


def build_notebook_raw() -> dict:
    """Build notebook dict without nbformat (pure stdlib)."""
    cells = []

    # Cell 1: Markdown
    cells.append({
        "cell_type": "markdown",
        "id":        make_uid(),
        "metadata":  {},
        "source":    CELL_1_MD,
    })

    # Code cells
    for filename, cell_type in CELL_FILES:
        path = CELLS_DIR / filename
        if not path.exists():
            print(f"  WARNING: {filename} not found - skipping")
            continue
        source = path.read_text(encoding="utf-8")
        if cell_type == "code":
            cells.append({
                "cell_type":       "code",
                "execution_count": None,
                "id":              make_uid(),
                "metadata":        {},
                "outputs":         [],
                "source":          source,
            })
        else:
            cells.append({
                "cell_type": "markdown",
                "id":        make_uid(),
                "metadata":  {},
                "source":    source,
            })

    return {
        "nbformat":       4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language":     "python",
                "name":         "python3",
            },
            "language_info": {
                "name":    "python",
                "version": "3.11.0",
            },
        },
        "cells": cells,
    }


def build_notebook_nbformat() -> "nbformat.NotebookNode":
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language":     "python",
        "name":         "python3",
    }
    nb.metadata["language_info"] = {"name": "python", "version": "3.11.0"}

    # Cell 1: Markdown
    nb.cells.append(nbformat.v4.new_markdown_cell(CELL_1_MD))

    # Code cells
    for filename, cell_type in CELL_FILES:
        path = CELLS_DIR / filename
        if not path.exists():
            print(f"  WARNING: {filename} not found - skipping")
            continue
        source = path.read_text(encoding="utf-8")
        if cell_type == "code":
            nb.cells.append(nbformat.v4.new_code_cell(source))
        else:
            nb.cells.append(nbformat.v4.new_markdown_cell(source))

    return nb


def main():
    print("Assembling Deep Notes AI notebook...")
    print(f"  Reading cells from : {CELLS_DIR}")
    print(f"  Output             : {OUTPUT_PATH}")
    print()

    if USE_NBFORMAT:
        print("  Using nbformat library")
        nb = build_notebook_nbformat()
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            nbformat.write(nb, f)
        cell_count = len(nb.cells)
    else:
        print("  Using stdlib json (nbformat not installed)")
        nb_dict = build_notebook_raw()
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(nb_dict, f, indent=1, ensure_ascii=False)
        cell_count = len(nb_dict["cells"])

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print()
    print(f"✅ Notebook created: {OUTPUT_PATH}")
    print(f"   Cells  : {cell_count}")
    print(f"   Size   : {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
