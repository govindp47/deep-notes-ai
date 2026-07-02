# ─── Cell 20: LangGraph StateGraph Assembly ──────────────────────────────────

builder = StateGraph(PipelineState)

# Add all nodes
builder.add_node("url_processor",        url_processor)
builder.add_node("transcript_extractor", transcript_extractor)
builder.add_node("note_generator",       note_generator)
builder.add_node("topic_extractor",      topic_extractor)
builder.add_node("topic_mapper",         topic_mapper)
builder.add_node("topic_canonicalizer",  topic_canonicalizer)
builder.add_node("graph_writer",         graph_writer_node)
builder.add_node("topic_aggregator",     topic_aggregator)
builder.add_node("summary_generator",    summary_generator_node)

# Entry point
builder.add_edge(START, "url_processor")

# Conditional routing: bail out early on no valid input
builder.add_conditional_edges(
    "url_processor",
    _route_after_url_processor,
    {"transcript_extractor": "transcript_extractor", END: END},
)
builder.add_conditional_edges(
    "transcript_extractor",
    _route_after_transcript_extractor,
    {"note_generator": "note_generator", END: END},
)

# Sequential pipeline
builder.add_edge("note_generator",      "topic_extractor")
builder.add_edge("topic_extractor",     "topic_mapper")
builder.add_edge("topic_mapper",        "topic_canonicalizer")
builder.add_edge("topic_canonicalizer", "graph_writer")
builder.add_edge("graph_writer",        "topic_aggregator")
builder.add_edge("topic_aggregator",    "summary_generator")
builder.add_edge("summary_generator",   END)

# Compile
pipeline = builder.compile()

print("✅ LangGraph pipeline compiled successfully")
print()
print("Pipeline nodes:")
for node_name in [
    "url_processor", "transcript_extractor", "note_generator",
    "topic_extractor", "topic_mapper", "topic_canonicalizer",
    "graph_writer", "topic_aggregator", "summary_generator"
]:
    print(f"   -> {node_name}")

# Display graph diagram
try:
    from IPython.display import Image, display
    img_bytes = pipeline.get_graph().draw_mermaid_png()
    display(Image(img_bytes))
    print("\n[Pipeline graph rendered above]")
except Exception:
    print("\nMermaid diagram source:")
    print(pipeline.get_graph().draw_mermaid())
