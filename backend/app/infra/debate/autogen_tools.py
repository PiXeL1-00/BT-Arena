"""Evidence retrieval tools for AutoGen debate agents.

Provides ``FunctionTool`` wrappers that agents can call mid-conversation
to actively query the evidence pack rather than relying solely on what
was included in the system prompt.
"""

from __future__ import annotations

from autogen_core.tools import FunctionTool


def build_evidence_tools(evidence_packets: list[dict]) -> list[FunctionTool]:
    """Build ``FunctionTool`` instances scoped to the given evidence packets.

    Each tool is a closure over the evidence list so IDs resolve correctly.
    """
    evidence_by_id: dict[str, dict] = {ep["eid"]: ep for ep in evidence_packets}

    def get_evidence(eid: str) -> str:
        """Retrieve a specific evidence packet by its ID."""
        ep = evidence_by_id.get(eid)
        if ep is None:
            available = list(evidence_by_id.keys())
            return f"Evidence {eid} not found. Available IDs: {available}"
        return (
            f"[{ep['eid']}] {ep['summary']} "
            f"(Source: {ep['source']}, Date: {ep['date']})"
        )

    def list_evidence() -> str:
        """List all available evidence IDs and their summaries."""
        if not evidence_packets:
            return "No evidence packets available."
        lines = [
            f"[{ep['eid']}] {ep['summary'][:80]}..."
            for ep in evidence_packets
        ]
        return "\n".join(lines)

    def search_evidence(query: str) -> str:
        """Search evidence summaries by keyword or phrase."""
        query_lower = query.lower()
        matches = [
            f"[{ep['eid']}] {ep['summary']}"
            for ep in evidence_packets
            if query_lower in ep["summary"].lower()
        ]
        if not matches:
            available = list(evidence_by_id.keys())
            return f"No evidence matches '{query}'. Available IDs: {available}"
        return "\n".join(matches)

    return [
        FunctionTool(
            get_evidence,
            description="Retrieve a specific evidence packet by its ID",
        ),
        FunctionTool(
            list_evidence,
            description="List all available evidence IDs and summaries",
        ),
        FunctionTool(
            search_evidence,
            description="Search evidence summaries by keyword",
        ),
    ]
