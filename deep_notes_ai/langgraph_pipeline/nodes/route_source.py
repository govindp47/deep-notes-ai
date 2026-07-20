"""
deep_notes_ai/langgraph_pipeline/nodes/route_source.py

Node: route_source

Responsibility: Validate the source and source_type, ensuring they are supported.
Nothing else.

Reads from state: source, source_type
Returns: dict (empty, as state is unchanged)
Error handling: Raises UnsupportedSourceTypeError or UnsupportedSourceError.
"""
from __future__ import annotations

import logging
from pathlib import Path

from deep_notes_ai.domain.models import SourceType, UnsupportedSourceTypeError, UnsupportedSourceError
from deep_notes_ai.langgraph_pipeline.state import PipelineState

logger = logging.getLogger(__name__)


def make_route_source_node(base_dir: Path):
    """
    Factory that returns a route_source node bound to the output base_dir.
    
    Args:
        base_dir: Settings.output_base_dir
        
    Returns:
        A callable compatible with LangGraph node interface.
    """

    def route_source(state: PipelineState) -> dict:
        """
        Validate the source type and source, and compute the execution directory.
        
        Reads:
            state["source"]: str
            state["source_type"]: SourceType
            
        Returns:
            {
                "current_run_dir": Path
            }
            
        Raises:
            UnsupportedSourceTypeError: if the source_type is invalid.
            UnsupportedSourceError: if the source is invalid for the type.
        """
        source = state.get("source")
        source_type = state.get("source_type")
        
        logger.info("Routing source: %s, type: %s", source, source_type)
        
        if not isinstance(source_type, SourceType):
            try:
                source_type = SourceType(source_type)
            except ValueError as exc:
                raise UnsupportedSourceTypeError(f"Invalid source type: {source_type}") from exc
                
        if not source:
            raise UnsupportedSourceError("Source cannot be empty.")
            
        # Validation logic specific to type could go here if needed, 
        # but basic validation is enough for the router.
        
        content_base_dir = base_dir / source_type.value
        
        return {"content_base_dir": content_base_dir}

    return route_source

