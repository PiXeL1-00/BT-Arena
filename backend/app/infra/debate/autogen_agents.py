"""AutoGen agent definitions for adversarial debate roles.

All 4 agents (Orthodox, Heretic, Skeptic, Judge) share the same model_client
so the evaluation is fair: we test how well a *single* LLM argues both sides
and judges impartially.
"""

from __future__ import annotations

from typing import Sequence

from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient
from autogen_core.tools import FunctionTool

from app.core.domain.schemas import DebateRole
from app.infra.debate.prompts import case_packet_text, format_evidence

# Role-specific instructions appended after the shared case context.
_ROLE_INSTRUCTIONS: dict[str, str] = {
    DebateRole.ORTHODOX: (
        "Your role: Steelman the MAJORITY interpretation supporting this claim. "
        "Argue FOR the claim using cited evidence IDs (e.g. [CL01-E1]). "
        "Be specific, cite sources, and address counterarguments."
    ),
    DebateRole.HERETIC: (
        "Your role: Steelman the MINORITY / opposing interpretation. "
        "Argue AGAINST or challenge the claim using cited evidence IDs. "
        "Expose weaknesses, gaps, and contradictions in the supporting evidence."
    ),
    DebateRole.SKEPTIC: (
        "Your role: Rigorously question BOTH sides. "
        "Identify gaps, unsupported assumptions, and contradictions. "
        "You are not a tiebreaker — you stress-test all arguments."
    ),
    DebateRole.JUDGE: (
        "Evaluate ALL positions from the adversarial debate. "
        "Use ONLY the evidence IDs from the evidence pack.\n\n"
        "Output ONLY valid JSON matching this schema:\n"
        '{"verdict": "SUPPORTED or REFUTED or INSUFFICIENT", '
        '"confidence": 0.85, '
        '"evidence_used": ["E1", "E2"], '
        '"reasoning": "brief explanation (1-3 sentences)"}\n\n'
        "No extra text outside the JSON."
    ),
}

_AGENT_DESCRIPTIONS: dict[str, str] = {
    DebateRole.ORTHODOX: "Argues FOR the claim using cited evidence.",
    DebateRole.HERETIC: "Argues AGAINST the claim using cited evidence.",
    DebateRole.SKEPTIC: "Questions BOTH sides, identifies gaps and contradictions.",
    DebateRole.JUDGE: "Evaluates all arguments and renders a final verdict in JSON.",
}


def create_debate_agents(
    model_client: ChatCompletionClient,
    *,
    claim: str,
    topic: str,
    evidence_packets: list[dict],
    tools: Sequence[FunctionTool] | None = None,
) -> dict[str, AssistantAgent]:
    """Create all 4 debate agents sharing the same ``model_client``.

    Arguments are sanitised via ``case_packet_text()`` / ``format_evidence()``
    to guard against prompt injection.
    """
    evidence_text = format_evidence(evidence_packets)
    case_context = case_packet_text(
        claim=claim, topic=topic, evidence_text=evidence_text,
    )

    agents: dict[str, AssistantAgent] = {}
    for role in (DebateRole.ORTHODOX, DebateRole.HERETIC, DebateRole.SKEPTIC, DebateRole.JUDGE):
        role_label = "Judge" if role == DebateRole.JUDGE else f"{role.value} agent"
        system_message = (
            f"You are the {role_label} in a structured adversarial debate.\n\n"
            f"{case_context}\n\n"
            f"{_ROLE_INSTRUCTIONS[role]}"
        )
        # Only debate agents (not the Judge) get evidence-retrieval tools.
        agent_tools = list(tools) if tools and role != DebateRole.JUDGE else None

        agents[role] = AssistantAgent(
            name=role.value,
            model_client=model_client,
            system_message=system_message,
            description=_AGENT_DESCRIPTIONS[role],
            tools=agent_tools,
        )
    return agents
