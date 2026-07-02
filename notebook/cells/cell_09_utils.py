# ─── Cell 9: Cost Tracker & Token Utilities ──────────────────────────────────

class CostTracker:
    'Tracks cumulative token usage and estimated USD cost per model.'

    def __init__(self):
        self._usage: Dict[str, Dict[str, Any]] = {}
        self.total_cost: float = 0.0

    def record(self, model: str, input_tokens: int, output_tokens: int = 0):
        if model not in self._usage:
            self._usage[model] = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}
        costs = TOKEN_COSTS.get(model, {"input": 0.0, "output": 0.0})
        cost  = input_tokens * costs["input"] + output_tokens * costs.get("output", 0.0)
        self._usage[model]["input_tokens"]  += input_tokens
        self._usage[model]["output_tokens"] += output_tokens
        self._usage[model]["cost"]          += cost
        self.total_cost                     += cost

    def report(self) -> str:
        lines = [
            "",
            "╔══════════════════════════════════╗",
            "║       💰 Cost Report              ║",
            "╚══════════════════════════════════╝",
        ]
        for model, stats in self._usage.items():
            lines += [
                f"  {model}",
                f"    Input  tokens : {stats['input_tokens']:>10,}",
                f"    Output tokens : {stats['output_tokens']:>10,}",
                f"    Cost          : ${stats['cost']:>10.4f}",
            ]
        lines += [
            "  " + "-" * 34,
            f"  Total estimated : ${self.total_cost:>10.4f}",
            "",
        ]
        return "\n".join(lines)


cost_tracker = CostTracker()


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    'Return token count for text using tiktoken.'
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text, disallowed_special=()))


def chunk_text(text: str,
               max_tokens: int = MAX_TOKENS_PER_CHUNK,
               model: str = "gpt-4o-mini",
               overlap_tokens: int = 150) -> List[str]:
    'Split text into overlapping chunks that each fit within max_tokens.'
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")

    tokens = enc.encode(text, disallowed_special=())
    if len(tokens) <= max_tokens:
        return [text]

    chunks, start = [], 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunks.append(enc.decode(tokens[start:end]))
        if end >= len(tokens):
            break
        start = end - overlap_tokens

    return chunks


print("✅ CostTracker & token utilities ready")
print(f"   Max tokens per chunk : {MAX_TOKENS_PER_CHUNK:,}")
print(f"   Embedding batch size : {EMBEDDING_BATCH_SIZE}")
