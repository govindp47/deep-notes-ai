# 01 — System Overview

## Purpose

Deep Notes AI is a transcript-to-documentation pipeline.

Given a YouTube video URL (or video ID), the system:

1. Extracts the raw spoken transcript from YouTube.
2. Cleans and normalises the spoken transcript into professional written English.
3. Numbers every statement (point) so every piece of content has a stable reference.
4. Discovers the hierarchical topic structure already present in the transcript.
5. Validates and enriches that hierarchy into a UUID-keyed content store.
6. Generates structured markdown documentation for every leaf content region.
7. Generates concise revision-note summaries for every leaf content region.
8. Persists intermediate and final artefacts to disk.
9. Renders two complete markdown documents: a full-content document and a summary document.

The system's primary consumer is a learner who wants high-quality, structured notes from a video course without watching it. The secondary use is interview preparation via the dense summary output.

---

## End-to-End Workflow

```
YouTube Video ID
        │
        ▼
┌──────────────────────┐
│  Transcript Extract  │  YouTubeTranscriptApi → raw spoken text (one long string)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Transcript Cleaning │  LLM (GPT-4o-mini) → bullet-per-statement, noise removed
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Point Numbering     │  clean_bullet_output() → "1. ...\n2. ...\n..." file
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Hierarchy Generation│  LLM (GPT-5-mini) + structured output → TranscriptHierarchy JSON
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Hierarchy Expansion │  build_content_payloads() → PayloadResult
│  (CONTENT extraction)│     • ContentPayload list (UUID-keyed with transcript slices)
│                      │     • ContentStoreItem metadata dict
│                      │     • Lightweight Node hierarchy (TitleNode / ContentNode)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Structured Content  │  LLM batched (partitioned) → markdown per CONTENT node
│  Generation          │  Saved into nodes_content[uuid].content
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Summary Generation  │  LLM batched (partitioned) → revision notes per CONTENT node
│                      │  Saved into nodes_content[uuid].summary
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  JSON Persistence    │  nodes_hierarchy.json + nodes_content.json
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Markdown Rendering  │  build_markdown_document() × 2 (content + summary)
└──────────┬───────────┘
           │
           ▼
   course_content.md
   course_summary.md
```

---

## Major Pipeline Stages

| Stage | Input | Output | LLM? |
|-------|-------|--------|------|
| 1. Extract | YouTube video ID | Raw transcript string | No |
| 2. Clean | Raw transcript string | Bullet-list markdown file | Yes |
| 3. Number | Bullet markdown file | Numbered-point markdown file | No |
| 4. Hierarchy Generation | Numbered file | `TranscriptHierarchy` JSON | Yes |
| 5. Content Extraction | Hierarchy + numbered file | `PayloadResult` (in-memory) | No |
| 6. Structured Content | `ContentPayload` list | `nodes_content[id].content` | Yes |
| 7. Summary Generation | `StructuredContentPayload` list | `nodes_content[id].summary` | Yes |
| 8. Persist | In-memory state | `nodes_hierarchy.json`, `nodes_content.json` | No |
| 9. Markdown Rendering | JSON files | `course_content.md`, `course_summary.md` | No |

---

## Inputs

- **YouTube video ID** — e.g. `jGg_1h0qzaM`
- **Transcript title** — e.g. `"LangGraph Course"` (used as the document root heading)
- **LLM model names** — configurable at each stage
- **Partition counts** — `INITIAL_PARTITIONS = 4`, `FALLBACK_PARTITIONS = 6`
- **Retry limits** — `MAX_RETRIES = 2`

## Outputs

| File | Description |
|------|-------------|
| `yt_cleaned_*.md` | Cleaned, bullet-form transcript (intermediate) |
| `yt_cleaned_*_numbered.md` | Numbered-point transcript (intermediate) |
| `transcript_hierarchy_*.json` | `TranscriptHierarchy` model JSON (intermediate) |
| `nodes_hierarchy.json` | Lightweight `Node` hierarchy JSON |
| `nodes_content.json` | UUID-keyed `ContentStoreItem` dictionary |
| `course_content.md` | Full structured markdown document |
| `course_summary.md` | Concise revision-note markdown document |

---

## High-Level Architecture

The system is currently a **sequential, stateful script** embedded in a Jupyter notebook. All intermediate artefacts are written to files in the notebook's working directory. Global notebook variables carry state between cells.

The target architecture is a **LangGraph agent** that:

- Maintains a typed state object instead of global notebook variables.
- Executes each pipeline stage as an isolated LangGraph node.
- Persists artefacts through an injected persistence service.
- Retries LLM calls through an isolated retry service.
- Supports checkpointing so a failed run can resume from the last successful node.

---

## Processing Lifecycle

1. **Single invocation per video.** The pipeline processes one video end-to-end per run.
2. **LLM calls are batched.** Content generation and summarization split the transcript into equal-length partitions to manage token limits.
3. **Fallback partitioning.** If a batch returns the wrong number of items, the system increases partition count and retries.
4. **UUID-keyed content store.** Every CONTENT leaf node receives a UUID at extraction time. All subsequent stages use that UUID to locate and update content.
5. **Temporary ID mapping.** During LLM batch calls, UUIDs are temporarily replaced with short sequential IDs (`N1`, `N2`, ...) to reduce token count. The mapping is reversed after the call.
6. **Dual output.** The final markdown renderer produces the same document twice: once with full content and once with summaries.

---

## Design Philosophy

- **Information fidelity over brevity.** The cleaning and structuring stages preserve every educational claim traceable to the transcript. Only the summarization stage aggressively compresses.
- **Separation of structure from content.** The hierarchy generation stage discovers structure. The content generation stage produces the actual documentation. These are decoupled LLM calls.
- **Partition-based LLM orchestration.** Rather than sending the entire transcript in one call, the system partitions by character position to stay within context limits.
- **Immutable reference numbers.** Once assigned, transcript point numbers never change. All hierarchy nodes reference points by their stable number, not by position or text.
- **UUID identity.** Every CONTENT leaf node receives a UUID that flows through the entire pipeline from extraction to final JSON. Identity never changes.
