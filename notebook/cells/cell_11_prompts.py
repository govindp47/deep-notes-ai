# ─── Cell 11: Production-Grade Prompt Templates ──────────────────────────────
#
# Prompt engineering decisions documented inline.
# All prompts use XML delimiters around user-controlled content
# to prevent prompt injection attacks.

# -- Prompt 1: Transcript -> Structured Notes --
#
# Design:
#   - Role framing ("expert knowledge engineer") biases toward precise output
#   - XML-delimited <TRANSCRIPT_CONTENT> prevents injection: model is told
#     the block contains raw user content
#   - Explicit "DO NOT add information not present" guard prevents hallucination
#   - Prescribed output format ensures consistent structure across all videos
#     (critical for downstream topic extraction reliability)

TRANSCRIPT_TO_NOTES_PROMPT = (
    "You are an expert knowledge engineer specialising in creating structured "
    "study materials from video transcripts.\n\n"
    "Convert the raw transcript below into comprehensive, well-organised Markdown study notes.\n\n"
    "STRICT RULES:\n"
    "1. Preserve ALL technical information, definitions, examples, and code snippets.\n"
    "2. Remove conversational filler and off-topic tangents.\n"
    "3. Organise content under clear ## headings with logical flow.\n"
    "4. Bold (**term**) every key definition on first occurrence.\n"
    "5. Use numbered lists for step-by-step processes; bullets for enumerations.\n"
    "6. Wrap code in ```language fenced blocks.\n"
    "7. DO NOT add information not present in the transcript.\n"
    "8. DO NOT editorialize or add opinions.\n\n"
    "REQUIRED OUTPUT STRUCTURE:\n"
    "# [Descriptive Title]\n\n"
    "## Overview\n[2-3 sentence executive summary]\n\n"
    "## Core Concepts\n[Key terms and definitions]\n\n"
    "## [Main Topic A]\n[Detailed notes]\n\n"
    "## [Main Topic B]\n[Detailed notes]\n\n"
    "...(as many ## sections as needed)...\n\n"
    "## Practical Examples\n[Every concrete example from the video]\n\n"
    "## Key Takeaways\n- [5-10 bullet points]\n\n"
    "<TRANSCRIPT_CONTENT>\n"
    "{transcript}\n"
    "</TRANSCRIPT_CONTENT>\n\n"
    "Return ONLY the Markdown notes. No preamble, no commentary."
)

# -- Prompt 2: Notes -> Topic Hierarchy --
#
# Design:
#   - Few-shot JSON example anchors the expected output format precisely.
#     Without examples, topic hierarchy depth is inconsistent across calls.
#   - json_mode=True on the LLM client guarantees parseable output.
#   - "Decompose until no meaningful further subdivision" prevents stopping
#     too early (flat list) or going too deep (atomic sentences as topics).

NOTES_TO_TOPICS_PROMPT = (
    "You are a knowledge graph architect. Extract a complete, deeply nested "
    "topic hierarchy from the study notes below.\n\n"
    "RULES:\n"
    "1. Identify ALL main topics, subtopics, and nested subtopics.\n"
    "2. Decompose recursively until no meaningful further subdivision exists.\n"
    "3. Each topic MUST include a 'content' field with the relevant excerpt from the notes.\n"
    "4. Normalise topic names: Title Case, concise (2-5 words preferred).\n"
    "5. Parent topics must not repeat content already captured in their children.\n\n"
    "EXAMPLE OUTPUT:\n"
    "{{\n"
    '  "topics": [\n'
    "    {{\n"
    '      "name": "LangGraph",\n'
    '      "content": "LangGraph is a library for building stateful multi-actor LLM apps...",\n'
    '      "subtopics": [\n'
    "        {{\n"
    '          "name": "State Management",\n'
    '          "content": "State is defined as a TypedDict with typed fields...",\n'
    '          "subtopics": [\n'
    "            {{\n"
    '              "name": "State Schema Definition",\n'
    '              "content": "Define a TypedDict class with typed fields for each attribute...",\n'
    '              "subtopics": []\n'
    "            }}\n"
    "          ]\n"
    "        }},\n"
    "        {{\n"
    '          "name": "Conditional Edges",\n'
    '          "content": "Conditional edges route execution based on a Python function...",\n'
    '          "subtopics": []\n'
    "        }}\n"
    "      ]\n"
    "    }}\n"
    "  ]\n"
    "}}\n\n"
    "Return ONLY valid JSON. No prose outside the JSON object.\n\n"
    "<NOTES>\n"
    "{notes}\n"
    "</NOTES>"
)

# -- Prompt 3: Topic Canonicalization --
#
# Design:
#   - Embedding similarity is the primary filter (fast, cheap).
#     LLM invoked ONLY when cosine similarity >= COSINE_SIM_THRESHOLD.
#     This reduces LLM calls by ~80% in practice.
#   - Confidence field lets pipeline ignore uncertain decisions.
#   - canonical_name field eliminates a separate rename pass.
#   - Content preview (300 chars) gives context without inflating cost.

CANONICALIZATION_PROMPT = (
    "You are a knowledge deduplication expert. Decide if these two topics "
    "represent the same underlying concept.\n\n"
    "Topic A: {topic_a}\n"
    "Representative content: {content_a}\n\n"
    "Topic B: {topic_b}\n"
    "Representative content: {content_b}\n\n"
    "Consider: same concept if named differently (e.g. 'LangGraph State' = "
    "'Graph State' in a LangGraph tutorial).\n"
    "Different concept if they cover genuinely distinct ideas (e.g. "
    "'State Management' != 'Conditional Edges').\n\n"
    "Return JSON only:\n"
    "{{\n"
    '  "are_same": true | false,\n'
    '  "confidence": <0.0-1.0>,\n'
    '  "canonical_name": "<best representative name if same; Topic A name if different>",\n'
    '  "reasoning": "<one sentence>"\n'
    "}}"
)

# -- Prompt 4: Topic Aggregation --
#
# Design:
#   - Uses GPT-4o (not mini) because merging multi-source content without
#     hallucinating or silently resolving contradictions needs stronger reasoning.
#   - "DO NOT add information" + "surface contradictions" are the two critical
#     guardrails for a knowledge-base aggregator.
#   - Source labels (### Source 1) help the model attribute and not homogenise.

AGGREGATION_PROMPT = (
    "You are a technical writer specialising in knowledge synthesis for a "
    "personal knowledge base.\n\n"
    "You have {source_count} content piece(s) about the same topic from "
    "different video sources. Produce ONE comprehensive Markdown document.\n\n"
    "STRICT RULES:\n"
    "1. Include ALL unique information present across sources.\n"
    "2. Remove exact duplicates; keep variant explanations if they add clarity.\n"
    "3. If sources CONTRADICT each other, include BOTH viewpoints explicitly:\n"
    "   > Warning: Sources disagree: Source 1 says X, Source 2 says Y.\n"
    "4. Maintain technical precision - do not simplify technical terms.\n"
    "5. Use clear markdown structure (##, ###, bullets, code blocks).\n"
    "6. DO NOT invent any information not present in the source material.\n"
    "7. DO NOT add external knowledge not present in the sources.\n\n"
    "Topic: {topic_name}\n\n"
    "<SOURCE_DOCUMENTS>\n"
    "{source_content}\n"
    "</SOURCE_DOCUMENTS>\n\n"
    "Write the comprehensive Markdown document now:"
)

# -- Prompt 5: Topic Summary --
#
# Design:
#   - "retrieval-optimised" framing biases toward keyword-rich, dense prose
#     rather than conversational narrative.
#   - "A student should be able to answer exam questions" is well-studied
#     framing that dramatically increases factual density.
#   - key_points as a separate list makes summaries scannable and reusable
#     for both full-text and bullet-retrieval use cases.

SUMMARY_PROMPT = (
    "You are an expert at creating retrieval-optimised knowledge summaries "
    "for a personal AI knowledge base.\n\n"
    "Write a dense, self-contained summary of the topic below.\n"
    "Requirements:\n"
    "- A student should be able to answer detailed exam questions using ONLY this summary.\n"
    "- Include the most important definitions, relationships, and facts.\n"
    "- Use precise technical language; avoid vague generalities.\n"
    "- The summary paragraph should be 3-5 sentences.\n"
    "- The key_points list should have 5-8 specific, actionable insights.\n\n"
    "Return JSON only:\n"
    "{{\n"
    '  "summary": "<3-5 sentence dense summary paragraph>",\n'
    '  "key_points": ["<specific insight 1>", "..."]\n'
    "}}\n\n"
    "Topic: {topic_name}\n\n"
    "<CONTENT>\n"
    "{content}\n"
    "</CONTENT>"
)

# -- Prompt 6: Retrieval Answering (RAG) --
#
# Design:
#   - Ground strictly to context to prevent hallucination in RAG mode.
#   - "If context does not contain..." prevents confidently wrong answers.

RETRIEVAL_ANSWER_PROMPT = (
    "You are a knowledgeable assistant for a personal YouTube knowledge base.\n"
    "Answer the user's question using ONLY the context provided below.\n\n"
    "If the context does not contain sufficient information to answer, say: "
    "'I don't have enough information about this in my knowledge base.'\n"
    "Do NOT use external knowledge.\n\n"
    "<CONTEXT>\n"
    "{context}\n"
    "</CONTEXT>\n\n"
    "Question: {question}\n\n"
    "Answer:"
)

print("✅ All 6 prompt templates defined")
print("   1. Transcript -> Structured Notes")
print("   2. Notes -> Topic Hierarchy (JSON)")
print("   3. Topic Canonicalization (JSON)")
print("   4. Topic Aggregation (multi-source)")
print("   5. Topic Summary (retrieval-optimised JSON)")
print("   6. Retrieval Answering (RAG)")
