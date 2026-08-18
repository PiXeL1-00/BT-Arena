import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, Linkedin, Github, Globe, Mail, BookOpen } from "lucide-react";

export const metadata: Metadata = {
    title: "About Bittensor Arena",
    description:
        "Discover the Bittensor ecosystem. Explore decentralized AI subnets across models, compute, media, DeSci, and more.",
};

function SectionCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
    return (
        <div className={`glass-card p-6 sm:p-8 space-y-4 ${className}`}>
            {children}
        </div>
    );
}

export default function AboutPage() {
    return (
        <div className="flex flex-col min-h-screen bg-background">
            <main className="flex-1 overflow-y-auto pt-16 sm:pt-20 pb-16 px-4 sm:px-6">
                <div className="max-w-3xl mx-auto space-y-10">

                    {/* Back link */}
                    <Link
                        href="/"
                        className="inline-flex items-center gap-2 text-sm text-[#292524]/60 hover:text-[#292524] transition-colors group"
                    >
                        <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
                        Back to Arena
                    </Link>

                    {/* Title */}
                    <header className="space-y-3">
                        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#292524]">
                            About Bittensor Arena
                        </h1>

                        <p className="text-lg sm:text-xl text-[#412AD1] font-medium font-serif italic">
                            Explore the decentralized intelligence economy.
                        </p>
                    </header>

                    {/* Intro */}
                    <section className="space-y-4 text-[#292524]/70 leading-relaxed">
                        <p>
                            Bittensor is a decentralized machine intelligence network where independent
                            teams build specialized AI services called <span className="text-[#292524] font-medium">subnets</span>.
                            Each subnet competes to provide useful intelligence while being rewarded by the network based on performance.
                        </p>

                        <p>
                            Rather than one model trying to solve every problem, Bittensor enables an
                            ecosystem of specialized networks focused on different domains: from language
                            models and compute marketplaces to scientific research and media generation.
                        </p>

                        <p>
                            This platform helps you discover, compare, and understand these subnet
                            categories so you can find the projects most relevant to your interests or applications.
                        </p>
                    </section>

                    {/* Bittensor Images removed temporarily */}
                    {/* <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="relative aspect-[4/5] rounded-xl overflow-hidden border border-[#292524]/10">
                            <Image
                                src="/bt_tao.webp"
                                alt="Bittensor Tao 3d image"
                                fill
                                className="object-cover"
                                sizes="(max-width: 640px) 100vw, 50vw"
                            />
                            <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-[#0C0A09]/70 to-transparent p-4">
                                <p className="text-sm text-[#FFFFFF] font-medium">TAO</p>
                            </div>
                        </div>
                        <div className="relative aspect-[4/5] rounded-xl overflow-hidden border border-[#292524]/10">
                            <Image
                                src="/bt_mesh.png"
                                alt="Graphical mesh of Bittensor"
                                fill
                                className="object-cover"
                                sizes="(max-width:640px) 100vw, 50vw"
                            />
                            <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-[#0C0A09]/70 to-transparent p-4">
                                <p className="text-sm text-[#FFFFFF] font-medium">Bittensor Network</p>
                            </div>
                        </div> 
                    </div> */}

                    {/* The Modern Problem */}
                    <SectionCard>
                        <h2 className="text-xl sm:text-2xl font-bold text-[#292524]">
                            Why Subnets?
                        </h2>

                        <div className="space-y-3 text-[#292524]/70 leading-relaxed">
                            <p>
                                Different AI problems require different architectures, incentives,
                                and expertise. Bittensor organizes these into specialized subnets
                                that evolve independently while contributing to the broader network.
                            </p>

                            <p>Examples include:</p>

                            <ul className="space-y-2">
                                {[
                                    "Large Language Models (LLMs)",
                                    "Inference & Compute Providers",
                                    "Image, Video & Media Generation",
                                    "DeSci (Decentralized Science)",
                                    "Data & Information Retrieval",
                                    "Agent Frameworks",
                                    "Financial Intelligence",
                                    "Predictive Systems",
                                    "Infrastructure & Validation",
                                ].map((item) => (
                                    <li key={item} className="flex items-start gap-2">
                                        <span className="mt-1.5 h-2 w-2 rounded-full bg-[#412AD1] shrink-0" />
                                        <span>{item}</span>
                                    </li>
                                ))}
                            </ul>

                            <p className="text-[#412AD1] font-semibold">
                                Every subnet contributes a different form of intelligence to the network.
                            </p>
                        </div>
                    </SectionCard>

                    {/* The Bittensor Standard */}
                    <SectionCard>
                        <h2 className="text-xl sm:text-2xl font-bold text-[#292524]">
                            Explore by Category
                        </h2>

                        <div className="space-y-3 text-[#292524]/70 leading-relaxed">
                            <p>
                                This platform organizes subnets into high-level categories to make the
                                rapidly growing Bittensor ecosystem easier to navigate.
                            </p>

                            <ul className="space-y-3">
                                {[
                                    {
                                        label: "AI Models",
                                        desc: "Language, multimodal, reasoning, and foundation model subnets."
                                    },
                                    {
                                        label: "Compute",
                                        desc: "GPU marketplaces, distributed inference, and decentralized compute."
                                    },
                                    {
                                        label: "Predictive Systems",
                                        desc: "Forecasts and analysis on Bittensor and various other ecosystems."
                                    },
                                    {
                                        label: "Media",
                                        desc: "Image, video, audio, and creative AI networks."
                                    },
                                    {
                                        label: "DeSci",
                                        desc: "Scientific research, biology, medicine, and open knowledge."
                                    },
                                    {
                                        label: "Data",
                                        desc: "Retrieval, indexing, datasets, and information services."
                                    },
                                    {
                                        label: "Infrastructure",
                                        desc: "Validators, tooling, monitoring, and network services."
                                    },
                                ].map(({ label, desc }) => (
                                    <li key={label} className="flex items-start gap-3">
                                        <span className="mt-1.5 h-2 w-2 rounded-full bg-[#412AD1] shrink-0" />
                                        <span>
                                            <span className="font-semibold text-[#292524]">{label}</span>
                                            <span className="text-[#292524]/70">: {desc}</span>
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </SectionCard>

                    { /*Add your OWN query, and watch the debate */ }
                    <SectionCard>
                        <h2 className="text-xl sm:text-2xl font-bold text-[#292524]">
                            Start Your Own Debate
                        </h2>

                        <div className="space-y-3 text-[#292524]/70 leading-relaxed">
                            <p>
                                Go beyond predefined subnet categories and start a debate around any topic
                                you want. Ask your own query directly in the textbox, and let the agents
                                analyze it, debate different perspectives, and work toward a shared conclusion.
                            </p>

                            <ul className="space-y-3">
                                {[
                                    {
                                        label: "Choose a Topic",
                                        desc: "Select from the available subnet categories, enter your own custom query, or combine both."
                                    },
                                    {
                                        label: "Select an Inference Provider",
                                        desc: "Choose the LLM model or inference provider you want the agents to use for the debate."
                                    },
                                    {
                                        label: "Watch the Debate",
                                        desc: "See the agents discuss your topic, challenge different perspectives, and reason through the available information."
                                    },
                                    {
                                        label: "Get the Final Conclusion",
                                        desc: "A judge agent evaluates the debate and delivers the final conclusion reached by the agents."
                                    },
                                ].map(({ label, desc }) => (
                                    <li key={label} className="flex items-start gap-3">
                                        <span className="mt-1.5 h-2 w-2 rounded-full bg-[#412AD1] shrink-0" />
                                        <span>
                                            <span className="font-semibold text-[#292524]">{label}</span>
                                            <span className="text-[#292524]/70">: {desc}</span>
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </SectionCard>

                    {/* What Bittensor Arena Does */}
                    <SectionCard>
                        <h2 className="text-xl sm:text-2xl font-bold text-[#292524]">
                            What You'll Find Here
                        </h2>

                        <div className="space-y-3 text-[#292524]/70 leading-relaxed">
                            <p>
                                Bittensor Arena provides an organized view of the Bittensor ecosystem,
                                making it easier to explore projects across different subnet categories.
                            </p>

                            <ul className="space-y-2">
                                {[
                                    "Browse subnets by category",
                                    "Discover emerging AI projects",
                                    "Understand each subnet's purpose",
                                    "Compare different areas of the ecosystem",
                                    "Navigate the decentralized AI landscape"
                                ].map((item) => (
                                    <li key={item} className="flex items-start gap-2">
                                        <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-[#29BC41] shrink-0" />
                                        <span>{item}</span>
                                    </li>
                                ))}
                            </ul>

                            <p className="text-[#412AD1] font-semibold pt-2">
                                Whether you're a developer, validator, miner, researcher, or simply
                                curious about decentralized AI, this platform is your gateway to the
                                Bittensor ecosystem.
                            </p>
                        </div>
                    </SectionCard>

                    {/* About Me */}
                    {/*Temporalily removed*/}
                    {/* <SectionCard className="border-primary/20">
                        <div className="flex flex-col sm:flex-row gap-5 items-start">
                            <div className="relative w-28 h-28 sm:w-32 sm:h-32 rounded-full overflow-hidden border-2 border-primary/30 shrink-0">
                                <Image
                                    src="/ateet.jpeg"
                                    alt="Ateet Bahamani"
                                    fill
                                    className="object-cover"
                                    sizes="128px"
                                />
                            </div>
                            <div>
                                <h2 className="text-xl sm:text-2xl font-bold text-foreground">About Me</h2>
                                <p className="text-sm font-medium text-primary tracking-wide mt-1">
                                    Ateet Bahamani &middot; AI Architect / AI Engineer
                                </p>
                            </div>
                        </div>
                        <div className="space-y-3 text-muted-foreground leading-relaxed">
                            <p>
                                I&apos;m Ateet Bahamani, an AI Architect building AI systems with one obsession: <span className="text-foreground font-medium">reliability at scale.</span>
                            </p>
                            <p>My work sits at the intersection of:</p>
                            <ul className="space-y-2 pl-1">
                                {[
                                    "LLM evaluation & analytics (measuring what matters, not what looks good)",
                                    "agentic workflows with guardrails (tools + memory + structure, without chaos)",
                                    "clean architecture (systems that stay maintainable as they grow)",
                                    "fullstack execution (backend + frontend, ship end-to-end)",
                                ].map((item) => (
                                    <li key={item} className="flex items-start gap-2">
                                        <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-accent shrink-0" />
                                        <span>{item}</span>
                                    </li>
                                ))}
                            </ul>
                            <p>
                                I build AI products that behave like responsible instruments: <span className="text-foreground font-medium">grounded, honest, and repeatable</span> : not just impressive demos.
                            </p>
                            <p>
                                If you&apos;re building with LLMs and you care about truthfulness, quality, and decision-grade reliability, I&apos;m always open to connect and collaborate.
                            </p>
                        </div>
                    </SectionCard> */}

                    {/* Links */}
                    {/*Temporalily removed*/}
                    {/* <SectionCard>
                        <h2 className="text-xl sm:text-2xl font-bold text-foreground">Links</h2>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {[
                                { icon: Linkedin, label: "LinkedIn", href: "https://www.linkedin.com/in/ateet-vatan-bahmani/" },
                                { icon: Github, label: "GitHub", href: "https://github.com/AteetVatan" },
                                { icon: BookOpen, label: "Blog", href: "https://ateetai.vercel.app/blog" },
                                { icon: Globe, label: "Portfolio", href: "https://ateetai.vercel.app" },
                                { icon: Mail, label: "Email", href: "mailto:ab@masxai.com" },
                            ].map(({ icon: Icon, label, href }) => (
                                <a
                                    key={label}
                                    href={href}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-3 rounded-xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-muted-foreground hover:text-cyan-300 hover:border-cyan-500/25 hover:bg-cyan-500/[0.06] transition-all duration-300"
                                >
                                    <Icon className="w-4 h-4 shrink-0" />
                                    {label}
                                </a>
                            ))}
                        </div>
                    </SectionCard> */}

                    <div className="h-4" />
                </div>
            </main>
        </div>
    );
}