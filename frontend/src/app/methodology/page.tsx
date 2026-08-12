import type { Metadata } from "next";
import Link from "next/link";
import {
    ArrowLeft,
    Database,
    Cpu,
    Globe,
    Swords,
    BarChart3,
    Activity,
    Zap,
    Radio,
    TrendingUp,
    AlertTriangle,
    Shield,
} from "lucide-react";
import { FlowNode } from "./FlowNode";
import { RoleCard } from "./RoleCard";
import { RubricBar } from "./RubricBar";
import styles from "./methodology.module.css";

export const metadata: Metadata = {
    title: "Methodology — Bittensor Arena",
    description:
        "Learn how Bittensor Arena uses AI to evaluate and rank Bittensor subnets across every category.",
};

const PIPELINE_STEPS = [
    {
        icon: Database,
        title: "Subnet Discovery",
        description: "Collect public information, documentation, and repositories",
        accent: "#412AD1",
    },
    {
        icon: Cpu,
        title: "AI Analysis",
        description: "LLMs analyze each subnet's purpose, features, and technical strengths",
        accent: "#B50BBB",
    },
    {
        icon: Swords,
        title: "Comparison",
        description: "Subnets compete only against others within the same category",
        accent: "#FCC503",
    },
    {
        icon: Shield,
        title: "Evaluation",
        description: "AI scores each subnet using a consistent evaluation framework",
        accent: "#29BC41",
    },
    {
        icon: BarChart3,
        title: "Rankings",
        description: "Generate category leaderboards and detailed subnet insights",
        accent: "#412AD1",
    },
] as const;

const ROLES = [
    {
        role: "Innovation",
        emoji: "💡",
        color: "#412AD1",
        stance: "Technical Originality",
        description:
            "Evaluates how uniquely the subnet contributes to the Bittensor ecosystem and advances decentralized AI.",
    },
    {
        role: "Execution",
        emoji: "⚙️",
        color: "#29BC41",
        stance: "Implementation Quality",
        description:
            "Assesses technical maturity, documentation, development activity, and project execution.",
    },
    {
        role: "Utility",
        emoji: "🚀",
        color: "#FCC503",
        stance: "Real-world Value",
        description:
            "Measures practical usefulness, adoption potential, and relevance within its category.",
    },
    {
        role: "Ecosystem Impact",
        emoji: "🌐",
        color: "#B50BBB",
        stance: "Network Contribution",
        description:
            "Evaluates how the subnet strengthens and complements the broader Bittensor ecosystem.",
    },
] as const;

const PHASES = [
    {
        phase: "Step 1",
        title: "Collect Information",
        badge: "Public Sources",
        description:
            "Gather documentation, repositories, websites, and publicly available information for every subnet.",
    },
    {
        phase: "Step 2",
        title: "Individual Analysis",
        badge: "AI Review",
        description:
            "Each subnet is independently analyzed to understand its goals, technology, strengths, and intended users.",
    },
    {
        phase: "Step 3",
        title: "Category Comparison",
        badge: "Peer Evaluation",
        description:
            "Subnets are compared only against others in the same category, ensuring fair and relevant rankings.",
    },
    {
        phase: "Step 4",
        title: "Scoring",
        badge: "Structured",
        description:
            "AI assigns scores across multiple evaluation dimensions using a consistent methodology.",
    },
    {
        phase: "Step 5",
        title: "Rankings",
        badge: "Leaderboard",
        description:
            "Scores are combined to produce category rankings and identify the highest-rated subnets.",
    },
] as const;

const RUBRIC = [
    {
        label: "Technical Innovation",
        range: "0–25 pts",
        width: "25%",
        gradient: "linear-gradient(90deg, #29BC41, #29BC41)",
        description:
            "Measures originality, technical sophistication, and advancement of decentralized AI.",
    },
    {
        label: "Execution Quality",
        range: "0–20 pts",
        width: "20%",
        gradient: "linear-gradient(90deg, #412AD1, #412AD1)",
        description:
            "Evaluates implementation quality, documentation, development activity, and overall project maturity.",
    },
    {
        label: "Utility",
        range: "0–20 pts",
        width: "20%",
        gradient: "linear-gradient(90deg, #B50BBB, #B50BBB)",
        description:
            "Assesses how effectively the subnet solves meaningful problems for users and developers.",
    },
    {
        label: "Ecosystem Contribution",
        range: "0–20 pts",
        width: "20%",
        gradient: "linear-gradient(90deg, #FCC503, #FCC503)",
        description:
            "Measures the subnet's impact on strengthening the broader Bittensor ecosystem.",
    },
    {
        label: "Growth Potential",
        range: "0–15 pts",
        width: "15%",
        gradient: "linear-gradient(90deg, #412AD1, #412AD1)",
        description:
            "Considers long-term sustainability, roadmap, adoption potential, and future relevance.",
    },
] as const;

function SectionCard({ children, id }: { children: React.ReactNode; id?: string }) {
    return (
        <section id={id} className="glass-card p-6 sm:p-8 space-y-5">
            {children}
        </section>
    );
}

function SectionTitle({ children, subtitle }: { children: React.ReactNode; subtitle?: string }) {
    return (
        <div className="space-y-1">
            <h2 className="text-xl sm:text-2xl font-bold text-[#292524]">{children}</h2>
            {subtitle && <p className="text-sm text-[#292524]/60">{subtitle}</p>}
        </div>
    );
}

export default function MethodologyPage() {
    return (
        <div className="flex flex-col min-h-screen bg-background">
            <main className="flex-1 overflow-y-auto pt-16 sm:pt-20 pb-16 px-4 sm:px-6">
                <div className="max-w-4xl mx-auto space-y-10">

                    <Link
                        href="/"
                        className="inline-flex items-center gap-2 text-sm text-[#292524]/60 hover:text-[#292524] transition-colors group"
                    >
                        <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
                        Back to Arena
                    </Link>

                    <header className="space-y-3">
                        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#292524]">
                            Methodology
                        </h1>

                        <p className="text-lg sm:text-xl text-[#412AD1] font-medium font-serif italic">
                            AI-powered evaluation for the Bittensor ecosystem
                        </p>

                        <p className="text-sm text-[#292524]/70 leading-relaxed max-w-2xl">
                            Bittensor Arena uses large language models to analyze and compare subnets
                            within each category. Rather than relying on popularity or manual rankings,
                            every subnet is evaluated using the same structured methodology to identify
                            the strongest projects based on their capabilities, technical merit, and
                            overall value proposition.
                        </p>
                    </header>

                    {/* ─── Section 1: Pipeline Overview ─── */}
                    <SectionCard id="pipeline">
                        <SectionTitle subtitle="From subnet discovery to category rankings">
                            AI Evaluation Pipeline
                        </SectionTitle>

                        <div className="flex flex-col md:flex-row items-center justify-center gap-0 py-4 overflow-x-auto">
                            {PIPELINE_STEPS.map((step, i) => (
                                <div key={step.title} className="flex flex-col md:flex-row items-center">
                                    <FlowNode
                                        icon={step.icon}
                                        title={step.title}
                                        description={step.description}
                                        accentColor={step.accent}
                                    />
                                    {i < PIPELINE_STEPS.length - 1 && (
                                        <div className={`${styles.connector} hidden md:block`} />
                                    )}
                                    {i < PIPELINE_STEPS.length - 1 && (
                                        <div className={`${styles.connectorVertical} md:hidden relative`} />
                                    )}
                                </div>
                            ))}
                        </div>
                    </SectionCard>

                    {/* ─── Section 2: Subnet categories ─── */}
                    <SectionCard id="categories">
                        <SectionTitle subtitle="What the evaluation process takes into consideration">
                            Evaluation Framework
                        </SectionTitle>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {ROLES.map((r) => (
                                <RoleCard key={r.role} {...r} />
                            ))}
                        </div>

                        <div className="rounded-xl border border-[#412AD1]/15 bg-[#412AD1]/[0.04] p-4 flex items-start gap-3">
                            <AlertTriangle className="w-4 h-4 text-[#412AD1] mt-0.5 shrink-0" />
                            <div className="space-y-1">
                                <p className="text-sm font-semibold text-[#412AD1]">Consistent Evaluation</p>
                                <p className="text-xs text-[#292524]/70 leading-relaxed">
                                    Every subnet within a category is evaluated using the same prompt,
                                    criteria, and scoring methodology. This creates a level playing field,
                                    allowing projects to be compared consistently regardless of team size
                                    or community popularity.
                                </p>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <h3 className="text-base font-semibold text-[#292524]">Evaluation Process</h3>
                            <div className={styles.timeline}>
                                {PHASES.map((p) => (
                                    <div key={p.phase} className={`${styles.timelineNode} pb-5 last:pb-0`}>
                                        <div className="flex items-baseline gap-2 mb-1">
                                            <span className="text-xs font-mono text-[#412AD1]">{p.phase}</span>
                                            <span className="text-sm font-semibold text-[#292524]">{p.title}</span>
                                            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-[#292524]/10 text-[#292524]/70">
                                                {p.badge}
                                            </span>
                                        </div>
                                        <p className="text-xs text-[#292524]/70 leading-relaxed">{p.description}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </SectionCard>

                    {/* ─── Section 3: Scoring Rubric ─── */}
                    <SectionCard id="scoring">
                        <SectionTitle subtitle="The dimensions used to compare subnets within each category">
                            Evaluation Criteria
                        </SectionTitle>

                        <p className="text-xs text-[#292524]/70 leading-relaxed">
                            Every subnet is evaluated using a consistent set of criteria designed to
                            measure technical quality, ecosystem contribution, and long-term potential.
                            Scores are intended to provide an objective comparison between subnets
                            competing in the same category, not across different categories.
                        </p>

                        <div className="space-y-4">
                            {RUBRIC.map((r) => (
                                <RubricBar key={r.label} {...r} />
                            ))}
                        </div>

                        <div className="flex items-center gap-4 pt-2 text-xs text-[#292524]/70">
                            <div className="flex items-center gap-1.5">
                                <div className="w-3 h-3 rounded-sm bg-[#29BC41]" />
                                Evaluation dimensions
                            </div>
                        </div>
                    </SectionCard>

                    {/* ─── Section 4: Streaming & Analytics ─── */}
                    <SectionCard id="analytics">
                        <SectionTitle subtitle="Continuous AI evaluation and category leaderboards">
                            Live Ranking &amp; Analytics
                        </SectionTitle>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <div className="glass-card p-4 space-y-2">
                                <div className="flex items-center gap-2">
                                    <Radio className="w-4 h-4 text-[#412AD1]" />
                                    <span className="text-sm font-semibold text-[#292524]">Continous Evaluation</span>
                                </div>
                                <p className="text-xs text-[#292524]/70 leading-relaxed">
                                    As the Bittensor ecosystem evolves, new subnets and project updates can be
                                    re-evaluated to ensure rankings remain relevant and reflect the current state
                                    of each category.
                                </p>
                            </div>
                            <div className="glass-card p-4 space-y-2">
                                <div className="flex items-center gap-2">
                                    <Zap className="w-4 h-4 text-[#FCC503]" />
                                    <span className="text-sm font-semibold text-[#292524]">AI Comparison Engine</span>
                                </div>
                                <p className="text-xs text-[#292524]/70 leading-relaxed">
                                    Large language models compare subnets using the same evaluation framework,
                                    producing structured reasoning and consistent scoring across every category..
                                </p>
                            </div>
                            <div className="glass-card p-4 space-y-2">
                                <div className="flex items-center gap-2">
                                    <TrendingUp className="w-4 h-4 text-[#29BC41]" />
                                    <span className="text-sm font-semibold text-[#292524]">Category Rankings</span>
                                </div>
                                <p className="text-xs text-[#292524]/70 leading-relaxed">
                                    Evaluation scores are aggregated into category leaderboards, helping users
                                    quickly discover the strongest subnets within AI Models, Compute, Media,
                                    DeSci, Infrastructure, and other ecosystem sectors.
                                </p>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <h3 className="text-sm font-semibold text-[#292524]">Evaluation Flow</h3>
                            <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-0 text-xs font-mono text-[#292524]/70 py-2">
                                <span className="px-3 py-1.5 rounded-lg border border-[#292524]/10 bg-[#FFFFFF]">Subnet Metadata</span>
                                <span className="hidden sm:block text-[#412AD1] mx-2">→</span>
                                <span className="sm:hidden text-[#412AD1]">↓</span>
                                <span className="px-3 py-1.5 rounded-lg border border-[#292524]/10 bg-[#FFFFFF]">AI Analysis</span>
                                <span className="hidden sm:block text-[#412AD1] mx-2">→</span>
                                <span className="sm:hidden text-[#412AD1]">↓</span>
                                <span className="px-3 py-1.5 rounded-lg border border-[#292524]/10 bg-[#FFFFFF]">Evaluation Engine</span>
                                <span className="hidden sm:block text-[#412AD1] mx-2">→</span>
                                <span className="sm:hidden text-[#412AD1]">↓</span>
                                <span className="px-3 py-1.5 rounded-lg border border-[#292524]/10 bg-[#FFFFFF]">Category Scores</span>
                                <span className="hidden sm:block text-[#412AD1] mx-2">→</span>
                                <span className="sm:hidden text-[#412AD1]">↓</span>
                                <span className="px-3 py-1.5 rounded-lg border border-[#412AD1]/20 bg-[#412AD1]/[0.06] text-[#412AD1]">Rankings & Explorer</span>
                            </div>
                        </div>
                    </SectionCard>
                    <p className="text-xs text-muted-foreground leading-relaxed pt-2">
                        Rankings are designed to provide a structured, AI-assisted perspective on
                        the Bittensor ecosystem. They should be viewed as a decision-support tool
                        that helps users compare projects within a category, while encouraging
                        further exploration of each subnet's documentation and technical details.
                    </p>
                    <div className="h-4" />
                </div>
            </main>
        </div>
    );
}
