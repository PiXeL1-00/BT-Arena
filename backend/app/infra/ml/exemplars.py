"""Pre-defined exemplar sentences for semantic falsifiability scoring.

Each list contains high-quality reference sentences for one dimension of
falsifiability.  These are embedded once by the export script and saved
as ``exemplars.npz``; at runtime only the pre-computed embeddings are used.
"""

from __future__ import annotations

# --- Mechanism: causal / explanatory language ---
MECHANISM_EXEMPLARS: list[str] = [
    "X causes Y through the following mechanism",
    "The causal pathway involves A leading to B",
    "This effect is produced by the interaction between",
    "The underlying process that drives this outcome is",
    "A leads to B because of a direct biochemical interaction",
    "The mechanism can be explained by increased pressure on",
    "This phenomenon results from a chain reaction starting with",
    "The root cause is a disruption in the feedback loop between",
    "Elevated levels of X trigger downstream effects on Y",
    "The observed change is driven by structural alterations in",
]

# --- Limitation: acknowledges caveats or uncertainty ---
LIMITATION_EXEMPLARS: list[str] = [
    "However, this analysis has limitations because",
    "The uncertainty in this conclusion stems from",
    "A major caveat is that the sample size was too small to",
    "These findings may not generalise to other populations",
    "One important limitation is the lack of longitudinal data",
    "The confidence interval is wide, suggesting substantial uncertainty",
    "This interpretation is tentative given the confounding factors",
    "We cannot rule out alternative explanations such as",
    "The evidence is mixed and does not conclusively establish",
    "Measurement error could account for part of the observed effect",
]

# --- Testability: proposes verifiable / falsifiable conditions ---
TESTABILITY_EXEMPLARS: list[str] = [
    "This could be falsified by observing",
    "If X then we would expect Y to be measurable",
    "An experiment to verify this would involve",
    "This prediction can be tested by comparing",
    "A replication study with a larger sample would confirm or refute",
    "If the hypothesis is correct, we should observe a decline in",
    "The claim would be disproven if future measurements show",
    "To validate this, one could run a controlled trial where",
    "Observable consequences of this theory include",
    "A natural experiment in which conditions change would test whether",
]
