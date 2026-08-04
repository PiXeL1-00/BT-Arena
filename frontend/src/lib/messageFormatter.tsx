import { ROLE_COLORS } from "./constants";
import type {
    ParsedMessage,
    Proposal,
    QuestionsMessage,
    AnswersMessage,
    Revision,
    DisputeQuestionsMessage,
    DisputeAnswersMessage,
    JudgeDecision,
} from "./types";

/**
 * Format structured message as React elements
 * Returns JSX.Element for consistent typing
 */
export function formatStructuredMessage(
    parsed: ParsedMessage,
    role: string,
    modelKey: string
): JSX.Element {
    const { type, data, isTruncated } = parsed;

    // Common header component
    const Header = () => (
        <div className="flex items-center gap-2 mb-2">
            <span
                className={`text-xs font-medium ${ROLE_COLORS[role] ?? "text-white/60"}`}
            >
                {role}
            </span>
            <span className="text-xs text-white/50 font-mono">{modelKey}</span>
            {isTruncated && (
                <span className="bg-orange-500/20 text-orange-300 text-xs px-2 py-1 rounded-full border border-orange-500/30">
                    ⚠️ Truncated
                </span>
            )}
        </div>
    );

    switch (type) {
        case "proposal":
            return formatProposal(data as Proposal, Header);
        case "questions":
            return formatQuestions(data as QuestionsMessage, Header);
        case "answers":
            return formatAnswers(data as AnswersMessage, Header);
        case "revision":
            return formatRevision(data as Revision, Header);
        case "dispute_questions":
            return formatDisputeQuestions(data as DisputeQuestionsMessage, Header);
        case "dispute_answers":
            return formatDisputeAnswers(data as DisputeAnswersMessage, Header);
        case "judge_decision":
            return formatJudgeDecision(data as JudgeDecision, Header);
        default:
            return (
                <div>
                    <Header />
                    <p className="text-xs text-red-300">Invalid message type</p>
                </div>
            );
    }
}

/**
 * Format verdict badge
 */
function VerdictBadge({ verdict }: { verdict: string }) {
    const colors =
        verdict === "SUPPORTED"
            ? "bg-green-500/20 text-green-300 border border-green-500/30"
            : verdict === "REFUTED"
                ? "bg-red-500/20 text-red-300 border border-red-500/30"
                : "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30";

    return (
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${colors}`}>
            {verdict}
        </span>
    );
}

/**
 * Extract creative label from key points content
 * Looks for phrases like "My point of view is", "My analysis is", "My findings are", etc.
 * Extracts the actual phrase from the content and uses it as the label
 */
function extractKeyPointsLabel(keyPoints: string[]): string {
    if (!keyPoints || keyPoints.length === 0) return "Key Points:";

    // First, try a simple extraction: look for "My [words] is/are" anywhere in the text
    for (const point of keyPoints) {
        const trimmed = point.trim();

        // Check if it starts with "My" (case insensitive) - most common case
        if (/^my\s/i.test(trimmed)) {
            // Extract "My [words] is/are" from the start
            const simpleMatch = trimmed.match(/^(my\s+[^.!?]+?\s+(?:is|are))\b/i);
            if (simpleMatch) {
                const phrase = simpleMatch[1];
                // Capitalize first letter of each word
                const capitalized = phrase
                    .split(' ')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                    .join(' ');
                return `${capitalized}:`;
            }
        }

        // Also check if "My [words] is/are" appears anywhere in the text (not just at start)
        const anywhereMatch = trimmed.match(/\b(my\s+[a-z]+(?:\s+[a-z]+)*\s+(?:is|are))\b/i);
        if (anywhereMatch) {
            const phrase = anywhereMatch[1];
            // Capitalize first letter of each word
            const capitalized = phrase
                .split(' ')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                .join(' ');
            return `${capitalized}:`;
        }
    }

    // Check all key points for patterns (not just the first one)
    for (const point of keyPoints) {
        // Patterns to match - more flexible, matches anywhere in text
        // Order matters: longer phrases first to avoid partial matches
        const patterns = [
            // "My point of view is" variations (longest first)
            { regex: /\b(my point of view is)\b/i, label: "My Point of View:" },
            // "My findings are/is" variations
            { regex: /\b(my findings (?:are|is))\b/i, label: "My Findings:" },
            // "My interpretation is" variations
            { regex: /\b(my interpretation is)\b/i, label: "My Interpretation:" },
            // "My understanding is" variations
            { regex: /\b(my understanding is)\b/i, label: "My Understanding:" },
            // "My assessment is" variations
            { regex: /\b(my assessment is)\b/i, label: "My Assessment:" },
            // "My evaluation is" variations
            { regex: /\b(my evaluation is)\b/i, label: "My Evaluation:" },
            // "My perspective is" variations
            { regex: /\b(my perspective is)\b/i, label: "My Perspective:" },
            // "My conclusion is" variations
            { regex: /\b(my conclusion is)\b/i, label: "My Conclusion:" },
            // "My observation is" variations
            { regex: /\b(my observation is)\b/i, label: "My Observation:" },
            // "My judgment is" variations
            { regex: /\b(my judgment is)\b/i, label: "My Judgment:" },
            // "My reasoning is" variations
            { regex: /\b(my reasoning is)\b/i, label: "My Reasoning:" },
            // "My analysis is" variations
            { regex: /\b(my analysis is)\b/i, label: "My Analysis:" },
            // "My argument is" variations
            { regex: /\b(my argument is)\b/i, label: "My Argument:" },
            // "My position is" variations
            { regex: /\b(my position is)\b/i, label: "My Position:" },
            // "My conviction is" variations
            { regex: /\b(my conviction is)\b/i, label: "My Conviction:" },
            // "My stance is" variations
            { regex: /\b(my stance is)\b/i, label: "My Stance:" },
            // "My verdict is" variations
            { regex: /\b(my verdict is)\b/i, label: "My Verdict:" },
            // "My belief is" variations
            { regex: /\b(my belief is)\b/i, label: "My Belief:" },
            // "My opinion is" variations
            { regex: /\b(my opinion is)\b/i, label: "My Opinion:" },
            // "My view is" variations (check after "point of view" to avoid duplicates)
            { regex: /\b(my view is)\b/i, label: "My View:" },
            // "My take is" variations
            { regex: /\b(my take is)\b/i, label: "My Take:" },
            // "My reading is" variations
            { regex: /\b(my reading is)\b/i, label: "My Reading:" },
        ];

        // Check for patterns in this point
        for (const { regex, label } of patterns) {
            const match = point.match(regex);
            if (match) {
                // Try to extract and capitalize the actual phrase from the text
                const matchedPhrase = match[1];
                if (matchedPhrase) {
                    // Capitalize first letter of each word
                    const capitalized = matchedPhrase
                        .split(' ')
                        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                        .join(' ');
                    return `${capitalized}:`;
                }
                return label;
            }
        }

        // More general pattern: "My [anything] is/are" - catch any creative phrase
        // Make it more flexible - allow any characters between "my" and "is/are"
        const generalMatch = point.match(/\b(my\s+[^\s]+(?:\s+[^\s]+)*?\s+(?:is|are))\b/i);
        if (generalMatch) {
            const matchedPhrase = generalMatch[1];
            if (matchedPhrase) {
                // Capitalize first letter of each word
                const capitalized = matchedPhrase
                    .split(' ')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                    .join(' ');
                return `${capitalized}:`;
            }
        }

        // Even more flexible: "My [anything]" without requiring "is/are"
        const veryGeneralMatch = point.match(/\b(my\s+[a-z]+(?:\s+[a-z]+){0,5}?)\b/i);
        if (veryGeneralMatch && veryGeneralMatch[1].split(' ').length >= 2) {
            const matchedPhrase = veryGeneralMatch[1];
            const capitalized = matchedPhrase
                .split(' ')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                .join(' ');
            return `${capitalized}:`;
        }

        // Alternative patterns: "I believe", "I think", "In my view", etc.
        const altPatterns = [
            { regex: /\b(i believe)\b/i, label: "I Believe:" },
            { regex: /\b(i think)\b/i, label: "I Think:" },
            { regex: /\b(in my view)\b/i, label: "In My View:" },
            { regex: /\b(in my opinion)\b/i, label: "In My Opinion:" },
            { regex: /\b(from my perspective)\b/i, label: "From My Perspective:" },
            { regex: /\b(in my analysis)\b/i, label: "In My Analysis:" },
        ];

        for (const { regex, label } of altPatterns) {
            if (regex.test(point)) {
                return label;
            }
        }
    }

    // Creative fallback: Generate label based on content characteristics
    // Since no "My X is" patterns were found, analyze the content to create a label
    if (keyPoints.length > 0) {
        const firstPoint = keyPoints[0].toLowerCase();
        const allPoints = keyPoints.join(' ').toLowerCase();

        // Check for evidence-based language
        if (firstPoint.includes('evidence') || firstPoint.includes('data') ||
            firstPoint.includes('tracker') || firstPoint.includes('report') ||
            firstPoint.includes('source') || firstPoint.includes('study')) {
            return "Evidence-Based Analysis:";
        }

        // Check for conclusion language
        if (firstPoint.includes('conclusion') || firstPoint.includes('therefore') ||
            firstPoint.includes('thus') || firstPoint.includes('conclude')) {
            return "Conclusion:";
        }

        // Check for observation language
        if (firstPoint.includes('observation') || firstPoint.includes('note') ||
            firstPoint.includes('observe') || firstPoint.includes('notice')) {
            return "Observations:";
        }

        // Check for reasoning language
        if (firstPoint.includes('reasoning') || firstPoint.includes('because') ||
            firstPoint.includes('due to') || firstPoint.includes('reason')) {
            return "Reasoning:";
        }

        // Check for assessment/evaluation language
        if (firstPoint.includes('assessment') || firstPoint.includes('evaluate') ||
            firstPoint.includes('assess') || firstPoint.includes('judgment')) {
            return "Assessment:";
        }

        // Check for challenge/critique language
        if (firstPoint.includes('challenge') || firstPoint.includes('critique') ||
            firstPoint.includes('question') || firstPoint.includes('doubt') ||
            firstPoint.includes('uncertain') || firstPoint.includes('insufficient')) {
            return "Critical Analysis:";
        }

        // Check for factual statements starting with "The" or "For"
        if (firstPoint.startsWith('the ') || firstPoint.startsWith('for ') ||
            firstPoint.startsWith('in ') || firstPoint.startsWith('according')) {
            return "Key Findings:";
        }

        // Check for methodology concerns
        if (allPoints.includes('methodology') || allPoints.includes('method') ||
            allPoints.includes('tracker') || allPoints.includes('data source')) {
            return "Methodology Assessment:";
        }

        // Check for trend/pattern language
        if (firstPoint.includes('trend') || firstPoint.includes('pattern') ||
            firstPoint.includes('volatility') || firstPoint.includes('change')) {
            return "Trend Analysis:";
        }

        // Generic creative alternatives based on content
        const creativeLabels = [
            "Analysis:",
            "Findings:",
            "Insights:",
            "Assessment:",
            "Evaluation:",
            "Perspective:",
            "Viewpoint:",
        ];

        // Use a deterministic label based on number of points (so it's consistent)
        const index = keyPoints.length % creativeLabels.length;
        return creativeLabels[index];
    }

    // Final fallback
    return "Key Points:";
}

/**
 * Format proposal message
 */
function formatProposal(
    data: Proposal,
    Header: () => JSX.Element
): JSX.Element {
    return (
        <div>
            <Header />
            <div className="space-y-2">
                <div className="flex items-center gap-2">
                    <span className="text-xs text-white/60">Verdict:</span>
                    <VerdictBadge verdict={data.proposed_verdict} />
                </div>

                {data.key_points && data.key_points.length > 0 && (
                    <div>
                        <span className="text-xs text-white/60 mb-1 block">
                            {extractKeyPointsLabel(data.key_points)}
                        </span>
                        <ul className="list-disc list-inside text-xs text-white/80 space-y-1 ml-2">
                            {data.key_points.map((point, i) => (
                                <li key={i}>{point}</li>
                            ))}
                        </ul>
                    </div>
                )}

                {data.uncertainties && data.uncertainties.length > 0 && (
                    <details className="mt-2">
                        <summary className="text-xs text-white/50 cursor-pointer hover:text-white/70 transition">
                            Uncertainties ({data.uncertainties.length})
                        </summary>
                        <ul className="list-disc list-inside text-xs text-white/60 space-y-1 ml-2 mt-1">
                            {data.uncertainties.map((unc, i) => (
                                <li key={i}>{unc}</li>
                            ))}
                        </ul>
                    </details>
                )}

                {data.what_would_change_my_mind &&
                    data.what_would_change_my_mind.length > 0 && (
                        <details className="mt-2">
                            <summary className="text-xs text-white/50 cursor-pointer hover:text-white/70 transition">
                                What Would Change My Mind ({data.what_would_change_my_mind.length})
                            </summary>
                            <ul className="list-disc list-inside text-xs text-white/60 space-y-1 ml-2 mt-1">
                                {data.what_would_change_my_mind.map((item, i) => (
                                    <li key={i}>{item}</li>
                                ))}
                            </ul>
                        </details>
                    )}

                {data.evidence_used && data.evidence_used.length > 0 && (
                    <details className="mt-2">
                        <summary className="text-xs text-white/50 cursor-pointer hover:text-white/70 transition">
                            Evidence ({data.evidence_used.length})
                        </summary>
                        <div className="flex flex-wrap gap-1 mt-1 ml-2">
                            {data.evidence_used.map((eid, i) => (
                                <span
                                    key={i}
                                    className="glass-button text-white/80 font-mono text-xs px-2 py-1 rounded-full"
                                >
                                    {eid}
                                </span>
                            ))}
                        </div>
                    </details>
                )}
            </div>
        </div>
    );
}

/**
 * Format questions message
 */
function formatQuestions(
    data: QuestionsMessage,
    Header: () => JSX.Element
): JSX.Element {
    return (
        <div>
            <Header />
            <div className="space-y-3">
                {data.questions.map((q, i) => (
                    <div key={i} className="glass-button rounded-xl p-3">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs text-white/50">To:</span>
                            <span className="text-xs font-medium text-cyan-300">
                                {q.to}
                            </span>
                        </div>
                        <p className="text-xs text-white/80 mb-2">{q.q}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}

/**
 * Format answers message
 */
function formatAnswers(
    data: AnswersMessage,
    Header: () => JSX.Element
): JSX.Element {
    const admissionColors: Record<string, string> = {
        none: "bg-white/10 text-white/70",
        insufficient: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30",
        uncertain: "bg-orange-500/20 text-orange-300 border border-orange-500/30",
    };

    return (
        <div>
            <Header />
            <div className="space-y-3">
                {data.answers.map((a, i) => (
                    <div key={i} className="glass-button rounded-xl p-3">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs text-white/50">Admission:</span>
                            <span
                                className={`text-xs px-2 py-1 rounded-full ${admissionColors[a.admission] || admissionColors.none
                                    }`}
                            >
                                {a.admission}
                            </span>
                        </div>
                        <div className="mb-2">
                            <span className="text-xs text-white/50">Q:</span>
                            <p className="text-xs text-white/60 italic ml-1">{a.q}</p>
                        </div>
                        <div className="mb-2">
                            <span className="text-xs text-white/50">A:</span>
                            <p className="text-xs text-white/80 ml-1">{a.a}</p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

/**
 * Format revision message
 */
function formatRevision(
    data: Revision,
    Header: () => JSX.Element
): JSX.Element {
    return (
        <div>
            <Header />
            <div className="space-y-2">
                <div className="flex items-center gap-2">
                    <span className="text-xs text-white/60">Final Verdict:</span>
                    <VerdictBadge verdict={data.final_proposed_verdict} />
                    {data.confidence !== undefined && (
                        <span className="text-xs text-white/60 ml-2">
                            Confidence: {Math.round(data.confidence * 100)}%
                        </span>
                    )}
                </div>

                {data.what_i_changed && data.what_i_changed.length > 0 && (
                    <div>
                        <span className="text-xs text-white/60 mb-1 block">
                            What I Changed:
                        </span>
                        <ul className="list-disc list-inside text-xs text-white/80 space-y-1 ml-2">
                            {data.what_i_changed.map((change, i) => (
                                <li key={i}>{change}</li>
                            ))}
                        </ul>
                    </div>
                )}

                {data.remaining_disagreements &&
                    data.remaining_disagreements.length > 0 && (
                        <div>
                            <span className="text-xs text-white/60 mb-1 block">
                                Remaining Disagreements:
                            </span>
                            <ul className="list-disc list-inside text-xs text-white/60 space-y-1 ml-2">
                                {data.remaining_disagreements.map((dis, i) => (
                                    <li key={i}>{dis}</li>
                                ))}
                            </ul>
                        </div>
                    )}
            </div>
        </div>
    );
}

/**
 * Format dispute questions message
 */
function formatDisputeQuestions(
    data: DisputeQuestionsMessage,
    Header: () => JSX.Element
): JSX.Element {
    return (
        <div>
            <Header />
            <div className="space-y-3">
                {data.questions.map((q, i) => (
                    <div key={i} className="glass-button rounded-xl p-3">
                        <p className="text-xs text-white/80 mb-2">{q.q}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}

/**
 * Format dispute answers message
 */
function formatDisputeAnswers(
    data: DisputeAnswersMessage,
    Header: () => JSX.Element
): JSX.Element {
    const admissionColors: Record<string, string> = {
        none: "bg-white/10 text-white/70",
        insufficient: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30",
        uncertain: "bg-orange-500/20 text-orange-300 border border-orange-500/30",
    };

    return (
        <div>
            <Header />
            <div className="space-y-3">
                {data.answers.map((a, i) => (
                    <div key={i} className="glass-button rounded-xl p-3">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs text-white/50">Admission:</span>
                            <span
                                className={`text-xs px-2 py-1 rounded-full ${admissionColors[a.admission] || admissionColors.none
                                    }`}
                            >
                                {a.admission}
                            </span>
                        </div>
                        <div className="mb-2">
                            <span className="text-xs text-white/50">Q:</span>
                            <p className="text-xs text-white/60 italic ml-1">{a.q}</p>
                        </div>
                        <div className="mb-2">
                            <span className="text-xs text-white/50">A:</span>
                            <p className="text-xs text-white/80 ml-1">{a.a}</p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

/**
 * Format judge decision message
 */
function formatJudgeDecision(
    data: JudgeDecision,
    Header: () => JSX.Element
): JSX.Element {
    return (
        <div>
            <Header />
            <div className="space-y-2">
                <div className="flex items-center gap-2">
                    <span className="text-xs text-white/60">Verdict:</span>
                    <VerdictBadge verdict={data.verdict} />
                    {data.confidence !== undefined && (
                        <span className="text-xs text-white/60 ml-2">
                            Confidence: {Math.round(data.confidence * 100)}%
                        </span>
                    )}
                </div>

                {data.reasoning && (
                    <div>
                        <span className="text-xs text-white/60 mb-1 block">Reasoning:</span>
                        <p className="text-xs text-white/80 leading-relaxed">
                            {data.reasoning}
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
