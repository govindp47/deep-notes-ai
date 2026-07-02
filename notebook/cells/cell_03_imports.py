# ─── Cell 3: Core Imports ────────────────────────────────────────────────────
import os, re, json, uuid, sqlite3, logging, operator, hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, TypedDict, Annotated
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed

import tiktoken
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log,
)
from pydantic import BaseModel, Field, field_validator, model_validator
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage

from langgraph.graph import StateGraph, END, START

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Optional: youtube-transcript-api error types
try:
    from youtube_transcript_api._errors import (
        TranscriptsDisabled, NoTranscriptFound, VideoUnavailable,
    )
except ImportError:
    try:
        from youtube_transcript_api import (
            TranscriptsDisabled, NoTranscriptFound, VideoUnavailable,
        )
    except ImportError:
        TranscriptsDisabled = NoTranscriptFound = VideoUnavailable = Exception

# Optional Neo4j
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

print("✅ All imports successful")
print(f"   Neo4j driver available: {NEO4J_AVAILABLE}")
