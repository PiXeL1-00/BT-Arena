"""Prompt templates for each debate phase -- all expect TOML output."""

from __future__ import annotations

import re
from typing import Any

from app.core.domain.schemas import DebateRole, VerdictEnum

from .schemas import AdmissionLevel, DebateTarget
from .toml_serde import dict_to_toml

_VERDICT_OPTIONS = "|".join(v.value for v in VerdictEnum)
_ADMISSION_OPTIONS = "|".join(a.value for a in AdmissionLevel)

# --- prompt injection sanitisation ---

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*:", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"<\|im_end\|>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"\[/INST\]", re.IGNORECASE),
    re.compile(r"```\s*(python|bash|sh|javascript|js)\b", re.IGNORECASE),
    re.compile(r"<script\b", re.IGNORECASE),
]


def _sanitize(text: str) -> str:
    """Strip prompt-injection patterns and TOML-breaking characters from user content."""
    cleaned = text
    for pat in _INJECTION_PATTERNS:
        cleaned = pat.sub("[REDACTED]", cleaned)
    # Strip markdown code fences that could confuse TOML parsing
    cleaned = cleaned.replace("```toml", "").replace("```", "")
    return cleaned


def format_evidence(evidence_packets: list[dict]) -> str:
    """Render evidence packets as a readable block for prompt inclusion."""
    lines = ["Evidence Packets:"]
    for ep in evidence_packets:
        lines.append(
            f'  [{_sanitize(ep["eid"])}] {_sanitize(ep["summary"])} '
            f'(Source: {_sanitize(ep["source"])}, Date: {_sanitize(ep["date"])})'
        )
    return "\n".join(lines)


def case_packet_text(
    *,
    claim: str,
    topic: str,
    evidence_text: str,
    pressure_text: str = "",
) -> str:
    """Moderator context block injected into every agent prompt."""
    parts = [
        f"Topic: {_sanitize(topic)}",
        f"Claim: {_sanitize(claim)}",
    ]
    if pressure_text:
        parts.append(f"Pressure context: {_sanitize(pressure_text)}")
    parts.append(evidence_text)  # already sanitised in format_evidence
    parts.append(
        "RULES: Use ONLY the evidence IDs above. "
        "Do NOT introduce outside facts. Be concise."
    )
    return "\n\n".join(parts)


# --- phase 1: proposals ---

_PROPOSAL_SCHEMA_HINT = f"""proposed_verdict = "{_VERDICT_OPTIONS}"
evidence_used = ["E1", "E2"]
key_points = ["point1", "point2"]
uncertainties = ["..."]
what_would_change_my_mind = ["..."]"""

_ROLE_INSTRUCTIONS: dict[str, str] = {
    DebateRole.ORTHODOX: (
        "Steelman the MAJORITY interpretation supporting this claim. "
        "Argue FOR the claim using cited evidence."
    ),
    DebateRole.HERETIC: (
        "Steelman the MINORITY / opposing interpretation. "
        "Argue AGAINST or challenge the claim using cited evidence."
    ),
    DebateRole.SKEPTIC: (
        "Rigorously question BOTH sides. "
        "Identify gaps, unsupported assumptions, and contradictions."
    ),
}


def proposal_prompt(*, role: str, case_packet: str) -> str:
    instruction = _ROLE_INSTRUCTIONS[role]
    return f"""You are the {role} agent in a structured debate.

{case_packet}

Your task: {instruction}
Cite specific evidence IDs (e.g. [CL01-E1]).

Output ONLY valid TOML matching this schema (no extra text):
{_PROPOSAL_SCHEMA_HINT}

Keep total response under 1200 characters. Return TOML only."""


def proposal_retry_prompt(*, role: str, case_packet: str, failed_output: str) -> str:
    instruction = _ROLE_INSTRUCTIONS[role]
    return f"""You are the {role} agent. Your previous response was not valid TOML.

{case_packet}

Your task: {instruction}

You MUST output ONLY valid TOML matching this exact schema:
{_PROPOSAL_SCHEMA_HINT}

Your previous invalid output was: {failed_output[:300]}

Return ONLY the TOML content. No markdown, no explanation."""


# --- phase 2: cross-exam ---

_QUESTIONS_SCHEMA_HINT = """[[questions]]
to = "<target_role>"
q = "your question"
evidence_refs = ["E1"]

[[questions]]
to = "<target_role>"
q = "your question"
evidence_refs = ["E2"]"""

_ANSWERS_SCHEMA_HINT = f"""[[answers]]
q = "the question"
a = "your answer"
evidence_refs = ["E1"]
admission = "{_ADMISSION_OPTIONS}"

[[answers]]
q = "the question"
a = "your answer"
evidence_refs = ["E2"]
admission = "{AdmissionLevel.NONE.value}"
"""


def cross_exam_question_prompt(
    *,
    asker: str,
    target: str,
    case_packet: str,
    asker_proposal_toml: str,
    target_proposal_toml: str,
    memo_text: str,
) -> str:
    return f"""You are the {asker} agent cross-examining the {target}.

{case_packet}

Your proposal:
{asker_proposal_toml}
{target}'s proposal:
{target_proposal_toml}

{memo_text}

Ask exactly 2 pointed questions to the {target}. Each question MUST:
- Reference at least one evidence ID (or explicitly ask about missing evidence)
- Challenge a specific claim or gap in {target}'s proposal

Output ONLY valid TOML:
{_QUESTIONS_SCHEMA_HINT}

Set "to" field to "{target}" for all questions.
Keep total response under 1200 characters. Return TOML only."""


def cross_exam_question_skeptic_prompt(
    *,
    case_packet: str,
    orthodox_proposal_toml: str,
    heretic_proposal_toml: str,
    memo_text: str,
) -> str:
    _s = DebateRole.SKEPTIC.value
    _o = DebateRole.ORTHODOX.value
    _h = DebateRole.HERETIC.value
    _both = DebateTarget.BOTH.value
    return f"""You are the {_s} agent questioning both {_o} and {_h}.

{case_packet}

{_o} proposal:
{orthodox_proposal_toml}
{_h} proposal:
{heretic_proposal_toml}

{memo_text}

Ask exactly 2 gap-hunting questions. You may address either {_o}, {_h}, or {_both}.
Each question MUST reference at least one evidence ID or ask about missing evidence.

Output ONLY valid TOML:
{_QUESTIONS_SCHEMA_HINT}

Keep total response under 1200 characters. Return TOML only."""


def cross_exam_answer_prompt(
    *,
    answerer: str,
    questions_toml: str,
    case_packet: str,
    own_proposal_toml: str,
    memo_text: str,
) -> str:
    return f"""You are the {answerer} agent answering cross-examination questions.

{case_packet}

Your proposal:
{own_proposal_toml}

{memo_text}

Questions to answer:
{questions_toml}

For each question, provide a direct answer. You MUST:
- Cite evidence IDs in your answer OR explicitly say "INSUFFICIENT evidence in pack"
- Set "admission" to "{AdmissionLevel.INSUFFICIENT.value}" if you lack evidence, \
"{AdmissionLevel.UNCERTAIN.value}" if you're unsure,
  or "{AdmissionLevel.NONE.value}" if you stand by your position

Output ONLY valid TOML:
{_ANSWERS_SCHEMA_HINT}

Keep total response under 1200 characters. Return TOML only."""


# --- phase 3: revision ---

_REVISION_SCHEMA_HINT = f"""final_proposed_verdict = "{_VERDICT_OPTIONS}"
evidence_used = ["E1", "E4"]
what_i_changed = ["description of any changes"]
remaining_disagreements = ["points still contested"]
confidence = 0.85"""


def revision_prompt(
    *,
    role: str,
    case_packet: str,
    own_proposal_toml: str,
    cross_exam_summary: str,
    memo_text: str,
) -> str:
    return f"""You are the {role} agent. The cross-examination phase is complete.

{case_packet}

Your original proposal:
{own_proposal_toml}

Cross-examination results:
{cross_exam_summary}

{memo_text}

Now REVISE your stance. Consider what you learned from the cross-examination.
You may change your verdict, evidence, or keep your original position.

Output ONLY valid TOML:
{_REVISION_SCHEMA_HINT}

Keep total response under 1200 characters. Return TOML only."""


# --- phase 3.5: dispute ---

_DISPUTE_Q_SCHEMA_HINT = """[[questions]]
q = "your decisive question"
evidence_refs = ["E1"]"""

_DISPUTE_A_SCHEMA_HINT = f"""[[answers]]
q = "the question"
a = "your answer"
evidence_refs = ["E1"]
admission = "{_ADMISSION_OPTIONS}"
"""


def dispute_question_prompt(
    *,
    case_packet: str,
    revisions_summary: str,
    memo_text: str,
) -> str:
    _s = DebateRole.SKEPTIC.value
    return f"""You are the {_s}. After revision, agents still disagree.

{case_packet}

Revisions:
{revisions_summary}

{memo_text}

Ask exactly 1 final decisive question that could resolve the disagreement.
It MUST reference specific evidence or point to the key gap.

Output ONLY valid TOML:
{_DISPUTE_Q_SCHEMA_HINT}

Keep total response under 800 characters. Return TOML only."""


def dispute_answer_prompt(
    *,
    answerer: str,
    case_packet: str,
    dispute_question_toml: str,
    own_revision_toml: str,
    memo_text: str,
) -> str:
    _s = DebateRole.SKEPTIC.value
    return f"""You are the {answerer} agent answering the {_s}'s final question.

{case_packet}

Your revised position:
{own_revision_toml}

{memo_text}

{_s}'s question:
{dispute_question_toml}

Provide a direct, final answer. Cite evidence or admit insufficiency.

Output ONLY valid TOML:
{_DISPUTE_A_SCHEMA_HINT}

Keep total response under 800 characters. Return TOML only."""


# --- phase 4: judge ---

_JUDGE_SCHEMA_HINT = f"""verdict = "{_VERDICT_OPTIONS}"
confidence = 0.85
evidence_used = ["E1", "E2"]
reasoning = "brief explanation (1-3 sentences)"
"""


def judge_prompt(
    *,
    claim: str,
    topic: str,
    evidence_text: str,
    structured_debate: list[dict[str, Any]],
) -> str:
    debate_block = dict_to_toml({"entry": structured_debate})
    _j = DebateRole.JUDGE.value
    return f"""You are the {_j}. Render a FINAL verdict on the claim.

Topic: {topic}
Claim: {claim}

{evidence_text}

Structured debate transcript (TOML entries from each agent phase):
{debate_block}

Evaluate ALL positions, cross-examination results, and revisions.
Use ONLY the evidence IDs from the evidence pack above.

Output ONLY valid TOML with these fields:
{_JUDGE_SCHEMA_HINT}

No extra text outside the TOML content."""


def toml_retry_suffix(*, failed_output: str, schema_hint: str) -> str:
    return (
        f"\n\nYour previous output was invalid TOML: {failed_output[:300]}\n"
        f"Return ONLY valid TOML matching:\n{schema_hint}"
    )
