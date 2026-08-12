"use client";

import { useState, useMemo } from "react";
import styles from "./MarsSimulation.module.css";

/* ----------------------------------------------------------------
   Editorial LLM data — curated ratings based on known model traits
   ---------------------------------------------------------------- */
interface LLMProfile {
    id: string;
    name: string;
    shortName: string;
    color: string;
    colorRGB: string;
    tagline: string;
    scores: Record<string, number>;
}

const LLMS: LLMProfile[] = [
    {
        id: "gpt4o",
        name: "GPT-4o",
        shortName: "GPT-4o",
        color: "#10b981",
        colorRGB: "16,185,129",
        tagline: "Best multimodal reasoning & tool use",
        scores: {
            planning: 92,
            operations: 88,
            lifeSupport: 90,
            comms: 85,
            robotics: 91,
            safety: 89,
        },
    },
    {
        id: "claude",
        name: "Claude Sonnet 4",
        shortName: "Claude 4",
        color: "#d97706",
        colorRGB: "217,119,6",
        tagline: "Strongest safety & instruction following",
        scores: {
            planning: 90,
            operations: 85,
            lifeSupport: 93,
            comms: 88,
            robotics: 82,
            safety: 96,
        },
    },
    {
        id: "mistral",
        name: "Mistral Large",
        shortName: "Mistral",
        color: "#8b5cf6",
        colorRGB: "139,92,246",
        tagline: "Fast multilingual with strong code",
        scores: {
            planning: 82,
            operations: 86,
            lifeSupport: 78,
            comms: 91,
            robotics: 80,
            safety: 81,
        },
    },
    {
        id: "deepseek",
        name: "DeepSeek Chat",
        shortName: "DeepSeek",
        color: "#06b6d4",
        colorRGB: "6,182,212",
        tagline: "Cost-efficient deep reasoning engine",
        scores: {
            planning: 88,
            operations: 84,
            lifeSupport: 80,
            comms: 79,
            robotics: 87,
            safety: 83,
        },
    },
    {
        id: "grok",
        name: "Grok-3",
        shortName: "Grok-3",
        color: "#ef4444",
        colorRGB: "239,68,68",
        tagline: "Real-time data access & bold reasoning",
        scores: {
            planning: 85,
            operations: 90,
            lifeSupport: 76,
            comms: 83,
            robotics: 84,
            safety: 78,
        },
    },
];

interface MissionDomain {
    key: string;
    emoji: string;
    title: string;
    description: string;
}

const DOMAINS: MissionDomain[] = [
    {
        key: "planning",
        emoji: "🛰️",
        title: "Mission Planning",
        description:
            "Trajectory optimization, fuel calculations, launch windows & scheduling",
    },
    {
        key: "operations",
        emoji: "🔧",
        title: "Real-Time Operations",
        description:
            "Anomaly detection, telemetry parsing, systems monitoring & emergency response",
    },
    {
        key: "lifeSupport",
        emoji: "🧬",
        title: "Life Support & Science",
        description:
            "Habitat monitoring, medical diagnostics, experiment design & analysis",
    },
    {
        key: "comms",
        emoji: "📡",
        title: "Communications",
        description:
            "Delay-tolerant messaging, data compression, protocol design & crew comms",
    },
    {
        key: "robotics",
        emoji: "🤖",
        title: "Autonomous Robotics",
        description:
            "Rover control, terrain mapping, resource extraction & construction planning",
    },
    {
        key: "safety",
        emoji: "🛡️",
        title: "Safety & Reliability",
        description:
            "Fault tolerance, prediction accuracy, hallucination resistance & risk assessment",
    },
];

/* ----------------------------------------------------------------
   Node positions along the trajectory (% of SVG viewBox width)
   ---------------------------------------------------------------- */
const NODE_POSITIONS = [
    { x: 22, y: 46 },
    { x: 35, y: 32 },
    { x: 50, y: 26 },
    { x: 65, y: 32 },
    { x: 78, y: 46 },
];

/* ================================================================
   Component
   ================================================================ */

export default function MarsSimulation() {
    const [hoveredLLM, setHoveredLLM] = useState<string | null>(null);

    /* Calculate overall Mars-readiness score per LLM */
    const rankings = useMemo(() => {
        return LLMS.map((llm) => {
            const values = Object.values(llm.scores);
            const avg =
                values.reduce((a, b) => a + b, 0) / values.length;
            return { llm, avg: Math.round(avg * 10) / 10 };
        }).sort((a, b) => b.avg - a.avg);
    }, []);

    const leader = rankings[0];

    /* SVG trajectory path */
    const trajectoryPath =
        "M 80,200 C 200,60 600,20 720,200";

    return (
        <div className={`${styles.starfield} space-y-8`}>
            {/* ===== HEADER ===== */}
            <div className="text-center space-y-2 relative z-10">
                <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#292524]">
                    Which LLM Will Get Us to Mars?
                </h2>
                <p className="text-sm text-[#292524]/70 max-w-xl mx-auto">
                    Rating 5 frontier LLMs across 6 critical Mars mission
                    domains — from trajectory planning to life support.
                </p>
            </div>

            {/* ===== TRAJECTORY HERO ===== */}
            <div className={styles.heroSection}>
                {/* Earth label */}
                <div className="absolute left-4 sm:left-8 top-1/2 -translate-y-1/2 flex flex-col items-center gap-3 z-10">
                    <div className={styles.earth} />
                    <span className={`${styles.planetLabel} text-blue-400`}>
                        Earth
                    </span>
                </div>

                {/* Mars label */}
                <div className="absolute right-4 sm:right-8 top-1/2 -translate-y-1/2 flex flex-col items-center gap-3 z-10">
                    <div className={styles.mars} />
                    <span className={`${styles.planetLabel} text-orange-400`}>
                        Mars
                    </span>
                </div>

                {/* SVG trajectory + particles */}
                <svg
                    viewBox="0 0 800 280"
                    className="w-full h-full absolute inset-0 z-1"
                    preserveAspectRatio="xMidYMid meet"
                >
                    <defs>
                        <linearGradient
                            id="arcGrad"
                            x1="0%"
                            y1="0%"
                            x2="100%"
                            y2="0%"
                        >
                            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.8" />
                            <stop offset="50%" stopColor="#67e8f9" stopOpacity="1" />
                            <stop offset="100%" stopColor="#c1440e" stopOpacity="0.8" />
                        </linearGradient>
                    </defs>

                    {/* Trajectory arc */}
                    <path
                        d={trajectoryPath}
                        fill="none"
                        stroke="url(#arcGrad)"
                        strokeWidth="2"
                        className={styles.trajectoryArc}
                    />

                    {/* Animated particles */}
                    {[1, 2, 3].map((i) => (
                        <circle
                            key={i}
                            className={`${styles.particle} ${styles[`particle${i}` as keyof typeof styles]}`}
                        >
                            <animateMotion
                                dur={`${5 + i}s`}
                                repeatCount="indefinite"
                                begin={`${(i - 1) * 2}s`}
                            >
                                <mpath href="#trajPath" />
                            </animateMotion>
                        </circle>
                    ))}
                    <path id="trajPath" d={trajectoryPath} fill="none" />
                </svg>

                {/* LLM Satellite Nodes */}
                {LLMS.map((llm, i) => {
                    const pos = NODE_POSITIONS[i];
                    return (
                        <div
                            key={llm.id}
                            className={styles.llmNode}
                            style={{
                                left: `${pos.x}%`,
                                top: `${pos.y}%`,
                                transform: "translate(-50%, -50%)",
                            }}
                            onMouseEnter={() => setHoveredLLM(llm.id)}
                            onMouseLeave={() => setHoveredLLM(null)}
                        >
                            <div
                                className={styles.nodeRing}
                                style={{
                                    borderColor: llm.color,
                                    color: llm.color,
                                    background: `rgba(${llm.colorRGB}, 0.1)`,
                                    boxShadow: hoveredLLM === llm.id
                                        ? `0 0 20px rgba(${llm.colorRGB}, 0.4)`
                                        : `0 0 10px rgba(${llm.colorRGB}, 0.2)`,
                                }}
                            >
                                <span className="text-xs font-bold" style={{ color: llm.color }}>
                                    {llm.shortName.charAt(0)}
                                </span>
                            </div>
                            <span className={styles.nodeLabel} style={{ color: llm.color }}>
                                {llm.shortName}
                            </span>
                        </div>
                    );
                })}
            </div>

            {/* ===== MISSION DOMAINS GRID ===== */}
            <div className="relative z-10">
                <h3 className="text-lg font-bold text-[#292524] mb-4 flex items-center gap-2">
                    <span className="w-1 h-5 bg-[#412AD1] rounded-full" />
                    Mission Domain Ratings
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {DOMAINS.map((domain) => (
                        <div key={domain.key} className="glass-panel rounded-2xl p-5 shadow-sm">
                            <div className="flex items-start gap-3 mb-4">
                                <span className="text-2xl leading-none">
                                    {domain.emoji}
                                </span>
                                <div>
                                    <h4 className="text-sm font-bold text-[#292524]">
                                        {domain.title}
                                    </h4>
                                    <p className="text-[11px] text-[#292524]/60 leading-relaxed mt-0.5">
                                        {domain.description}
                                    </p>
                                </div>
                            </div>

                            <div className="space-y-2.5">
                                {LLMS.map((llm) => {
                                    const score =
                                        llm.scores[domain.key] ?? 0;
                                    return (
                                        <div
                                            key={llm.id}
                                            className="flex items-center gap-2"
                                        >
                                            <span
                                                className="text-[10px] font-semibold w-16 truncate text-[#292524]"
                                            >
                                                {llm.shortName}
                                            </span>
                                            <div className="flex-1 bg-[#292524]/10 rounded-full h-2 overflow-hidden">
                                                <div
                                                    className="h-full rounded-full transition-all duration-500"
                                                    style={{
                                                        width: `${score}%`,
                                                        backgroundColor: llm.color,
                                                    }}
                                                />
                                            </div>
                                            <span className="text-[10px] font-mono text-[#292524]/70 w-7 text-right tabular-nums">
                                                {score}
                                            </span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* ===== MARS READINESS VERDICT ===== */}
            <div className="glass-panel rounded-3xl p-6 shadow-lg relative z-10">
                <div className="flex flex-col items-center gap-5">
                    <div className="text-center">
                        <h3 className="text-lg font-bold text-[#412AD1]">
                            Mars Readiness Verdict
                        </h3>
                        <p className="text-xs text-[#292524]/60 mt-1">
                            Composite score across all 6 mission domains
                        </p>
                    </div>

                    <div className="flex flex-wrap justify-center gap-3">
                        {rankings.map((r, i) => (
                            <div
                                key={r.llm.id}
                                className="flex flex-col items-center p-3 rounded-2xl bg-[#FFFFFF] border border-[#292524]/10 shadow-sm min-w-[80px]"
                            >
                                {i === 0 && (
                                    <span className="text-base mb-1">👑</span>
                                )}
                                <span
                                    className="text-xl font-extrabold tabular-nums text-[#292524]"
                                >
                                    {r.avg}
                                </span>
                                <span
                                    className="text-[10px] font-semibold text-[#412AD1]"
                                >
                                    {r.llm.shortName}
                                </span>
                            </div>
                        ))}
                    </div>

                    <p className="text-xs text-[#292524]/70 text-center max-w-lg leading-relaxed">
                        <span
                            className="font-bold text-[#412AD1]"
                        >
                            {leader.llm.name}
                        </span>{" "}
                        leads with a composite score of{" "}
                        <span className="text-[#292524] font-semibold">
                            {leader.avg}
                        </span>
                        , excelling in{" "}
                        {(() => {
                            const entries = Object.entries(
                                leader.llm.scores,
                            ).sort((a, b) => b[1] - a[1]);
                            const top2 = entries.slice(0, 2).map((e) => {
                                const domain = DOMAINS.find(
                                    (d) => d.key === e[0],
                                );
                                return domain?.title ?? e[0];
                            });
                            return top2.join(" and ");
                        })()}
                        . For humanity&apos;s most ambitious journey, a
                        multi-model approach combining each AI&apos;s strengths
                        is the safest path to Mars.
                    </p>
                </div>
            </div>

            {/* ===== FOOTER NOTE ===== */}
            <p className="text-[10px] text-[#292524]/50 text-center relative z-10 pb-4">
                Ratings are editorial assessments based on model capabilities
                as of Feb 2026. Not derived from benchmark data.
            </p>
        </div>
    );
}
