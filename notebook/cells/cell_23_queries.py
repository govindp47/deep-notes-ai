# ─── Cell 23: Query Examples & Results ───────────────────────────────────────
#
# Run this cell after Cell 22 to explore your knowledge base.

from IPython.display import Markdown, display

print("=" * 60)
print("Knowledge Base Query Examples")
print("=" * 60)

# -- 1. List all topics --
print("\nExample 1: All Topics in Knowledge Base")
print("-" * 40)
all_topics = list_all_topics()
print(f"Found {len(all_topics)} canonical topic(s):")
for t in all_topics:
    src = t['source_count']
    print(f"  [{src} video(s)] {t['canonical_name']}")
    if t.get("aliases") and len(t["aliases"]) > 1:
        others = [a for a in t["aliases"] if a != t["canonical_name"]]
        if others:
            print(f"             = {', '.join(others[:3])}")

# -- 2. Query a specific topic (auto-selects first available) --
print("\nExample 2: Query Specific Topic")
print("-" * 40)
if all_topics:
    first_topic = all_topics[0]["canonical_name"]
    result = query_topic(first_topic)
    if "error" not in result:
        print(f"Topic      : {result['canonical_name']}")
        print(f"Aliases    : {result['aliases']}")
        print(f"Sources    : {result['source_video_ids']}")
        print(f"Token count: {result['token_count']:,}")
        if result.get("key_points"):
            print("Key Points:")
            for kp in result["key_points"][:3]:
                print(f"  - {kp}")
    else:
        print(result["error"])

# -- 3. Topic summary (formatted) --
print("\nExample 3: Topic Summary (Formatted)")
print("-" * 40)
if all_topics:
    first_topic = all_topics[0]["canonical_name"]
    summary_md  = query_topic_summary(first_topic)
    try:
        display(Markdown(summary_md))
    except Exception:
        print(summary_md)

# -- 4. Video query (first processed video) --
print("\nExample 4: Full Video Knowledge")
print("-" * 40)
all_videos = sqlite_store.get_all_canonical_topics()
vid_result = sqlite_store.get_all_canonical_topics()
# Get actual video IDs from the database
with sqlite_store._conn() as c:
    vid_rows = c.execute("SELECT video_id, title FROM videos LIMIT 3").fetchall()

for row in vid_rows:
    vid = query_video(row["video_id"])
    if "error" not in vid:
        print(f"Video   : {vid['title']}")
        print(f"Topics  : {vid['total_topics']}")
        notes_preview = (vid['structured_notes'] or "")[:500]
        print(f"Notes   : {notes_preview}{'...' if len(vid.get('structured_notes', '')) > 500 else ''}")
        print()

# -- 5. Semantic search --
print("\nExample 5: Semantic Search")
print("-" * 40)
if all_topics:
    first_kw = all_topics[0]["canonical_name"]
    print(f"Query: '{first_kw}'")
    hits = search_topics_semantic(first_kw, top_k=3)
    for h in hits:
        print(f"  Score {h['score']:.3f}: {h['canonical_name']}")

# -- 6. RAG Q&A --
print("\nExample 6: RAG Question & Answer")
print("-" * 40)
if all_topics:
    question = f"What is {all_topics[0]['canonical_name']} and why is it important?"
    print(f"Q: {question}")
    print()
    answer = ask_knowledge_base(question, top_k=2)
    print(f"A: {answer[:600]}{'...' if len(answer) > 600 else ''}")

print()
print("Done! Use query_video(), query_topic(), and ask_knowledge_base() interactively.")
