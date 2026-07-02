# ─── Cell 4: Configuration & Environment ─────────────────────────────────────
load_dotenv()

# -- API Keys --
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise EnvironmentError(
        "OPENAI_API_KEY not found.\n"
        "   Add it to your .env file:  OPENAI_API_KEY=sk-..."
    )

# -- Optional: Neo4j --
NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# -- Optional: LangSmith tracing --
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
if LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"]    = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"]    = "deep-notes-ai"
    print("✅ LangSmith tracing enabled")
else:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

# -- Model selection --
# gpt-4o-mini: cheap extraction / summaries
# gpt-4o:      high-quality consolidation (aggregation)
# text-embedding-3-small: best cost/quality embedding
MODELS = {
    "extraction": "gpt-4o-mini",
    "reasoning":  "gpt-4o",
    "embedding":  "text-embedding-3-small",
}

# -- Token pricing ($ per token) --
TOKEN_COSTS: Dict[str, Dict[str, float]] = {
    "gpt-4o-mini":            {"input": 0.15  / 1_000_000, "output": 0.60  / 1_000_000},
    "gpt-4o":                 {"input": 2.50  / 1_000_000, "output": 10.00 / 1_000_000},
    "text-embedding-3-small": {"input": 0.02  / 1_000_000, "output": 0.0},
}

# -- Processing constants --
MAX_TOKENS_PER_CHUNK = 6_000    # safe for gpt-4o-mini 128k context
EMBEDDING_BATCH_SIZE = 100
COSINE_SIM_THRESHOLD = 0.85     # embedding pre-filter for canonicalization
CANON_LLM_CONFIDENCE = 0.70     # min LLM confidence to merge topics

# -- Storage paths --
DB_PATH = Path("./deep_notes.db")

# -- Logging --
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("deep-notes")

print("✅ Configuration loaded")
print(f"   Extraction model : {MODELS['extraction']}")
print(f"   Reasoning model  : {MODELS['reasoning']}")
print(f"   Embedding model  : {MODELS['embedding']}")
print(f"   Database path    : {DB_PATH.resolve()}")
