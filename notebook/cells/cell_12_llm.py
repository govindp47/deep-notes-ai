# ─── Cell 12: LLM Client Factory ─────────────────────────────────────────────

def make_llm(model: str,
             temperature: float = 0.0,
             json_mode: bool = False,
             max_tokens: Optional[int] = None) -> ChatOpenAI:
    'Factory that returns a configured ChatOpenAI client.'
    kwargs: Dict[str, Any] = {
        "model":          model,
        "temperature":    temperature,
        "openai_api_key": OPENAI_API_KEY,
        "max_retries":    2,
    }
    if json_mode:
        kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    return ChatOpenAI(**kwargs)


# Pre-warm clients (validates API key immediately)
print("Initialising LLM clients...")
_extraction_llm = make_llm(MODELS["extraction"], temperature=0.1)
_json_llm       = make_llm(MODELS["extraction"], temperature=0.0, json_mode=True)
_reasoning_llm  = make_llm(MODELS["reasoning"],  temperature=0.2)

print("✅ LLM clients ready")
print(f"   Extraction : {MODELS['extraction']}")
print(f"   Reasoning  : {MODELS['reasoning']}")
