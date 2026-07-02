# ─── Cell 22: End-to-End Demo Execution ──────────────────────────────────────
#
# Sample videos: two LangGraph tutorials - canonical topic merging will fire
# when the same concepts appear across both.
#
# CUSTOMIZE THIS CELL: replace with your own YouTube URLs.

DEMO_URLS = [
    # LangGraph intro series (two videos covering overlapping concepts)
    "https://www.youtube.com/watch?v=R8KB-Zcynxw",  # LangGraph intro
    "https://www.youtube.com/watch?v=v9fkbTxPzs0",  # LangGraph agents
]

print("╔══════════════════════════════════════════════════════════════╗")
print("║              Deep Notes AI - Pipeline Execution              ║")
print("╚══════════════════════════════════════════════════════════════╝")
print()
print(f"Processing {len(DEMO_URLS)} video(s):")
for u in DEMO_URLS:
    print(f"  - {u}")
print()

initial_state: PipelineState = {
    "urls":                DEMO_URLS,
    "video_documents":     [],
    "structured_notes":    {},
    "topic_trees":         {},
    "topic_nodes":         [],
    "canonical_topics":    [],
    "master_documents":    [],
    "summaries":           [],
    "errors":              [],
    "current_phase":       "init",
    "processing_complete": False,
}

# Stream execution for real-time progress
final_state = None
for step in pipeline.stream(initial_state, {"recursion_limit": 50}):
    for node_name, node_output in step.items():
        phase = node_output.get("current_phase", "")
        print(f"  [DONE] {node_name:30s} -> {phase}")
    final_state = list(step.values())[-1]

print()
print("╔══════════════════════════════════════════════════════════════╗")
print("║                    Pipeline Complete!                        ║")
print("╚══════════════════════════════════════════════════════════════╝")

if final_state:
    videos    = final_state.get("video_documents",  [])
    notes     = final_state.get("structured_notes", {})
    topics    = final_state.get("topic_nodes",      [])
    canonical = final_state.get("canonical_topics", [])
    summaries = final_state.get("summaries",        [])
    errors    = final_state.get("errors",           [])

    print()
    print("Results:")
    print(f"  Videos processed       : {len(videos)}")
    print(f"  Notes generated        : {len(notes)} video(s)")
    print(f"  Raw topic nodes        : {len(topics)}")
    print(f"  Canonical topics       : {len(canonical)}")
    print(f"  Topics merged          : {max(0, len(topics) - len(canonical))}")
    print(f"  Summaries generated    : {len(summaries)}")
    print(f"  Errors                 : {len(errors)}")

    if errors:
        print()
        print("Errors encountered:")
        for e in errors:
            print(f"  WARNING: {e}")

    print()
    print(cost_tracker.report())
