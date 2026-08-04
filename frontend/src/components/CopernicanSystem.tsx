"use client";

import { useEffect, useState } from "react";

export default function CopernicanSystem() {
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) return null;

    return (
        <div className="fixed inset-0 z-0 flex items-center justify-center overflow-hidden pointer-events-none select-none opacity-40">
            <div className="relative w-[1200px] h-[1200px] animate-slow-spin">
                <svg viewBox="0 0 1000 1000" className="w-full h-full">
                    <defs>
                        <filter id="ink-bleed" x="-20%" y="-20%" width="140%" height="140%">
                            <feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="3" result="noise" />
                            <feDisplacementMap in="SourceGraphic" in2="noise" scale="2" />
                        </filter>
                    </defs>

                    {/* Sun */}
                    <g className="sun-group">
                        <circle cx="500" cy="500" r="40" stroke="currentColor" strokeWidth="2" fill="none" className="text-cyan-500/80" />
                        <circle cx="500" cy="500" r="15" fill="currentColor" className="text-cyan-500/50" />
                        <text x="500" y="500" textAnchor="middle" dy="5" className="font-great-vibes text-2xl fill-cyan-200" style={{ fontFamily: 'var(--font-great-vibes)' }}>Sol</text>
                    </g>

                    {/* Orbits and Planets */}
                    {/* Mercury */}
                    <g className="orbit-group animate-[spin_8s_linear_infinite]" style={{ transformOrigin: "500px 500px" }}>
                        <circle cx="500" cy="500" r="80" stroke="currentColor" strokeWidth="1" fill="none" className="text-white/10" />
                        <circle cx="580" cy="500" r="4" fill="currentColor" className="text-slate-400" />
                        <path id="mercury-path" d="M 420,500 A 80,80 0 1,1 580,500 A 80,80 0 1,1 420,500" fill="none" />
                        <text className="font-great-vibes text-sm fill-slate-500" style={{ fontFamily: 'var(--font-great-vibes)' }}>
                            <textPath href="#mercury-path" startOffset="75%">Mercury</textPath>
                        </text>
                    </g>

                    {/* Venus */}
                    <g className="orbit-group animate-[spin_12s_linear_infinite]" style={{ transformOrigin: "500px 500px", animationDirection: "reverse" }}>
                        <circle cx="500" cy="500" r="130" stroke="currentColor" strokeWidth="1" fill="none" className="text-white/10" />
                        <circle cx="370" cy="500" r="6" fill="currentColor" className="text-indigo-300/60" />
                        <path id="venus-path" d="M 370,500 A 130,130 0 1,1 630,500 A 130,130 0 1,1 370,500" fill="none" />
                        <text className="font-great-vibes text-lg fill-indigo-300/40" style={{ fontFamily: 'var(--font-great-vibes)' }}>
                            <textPath href="#venus-path" startOffset="0%">Venus</textPath>
                        </text>
                    </g>

                    {/* Earth */}
                    <g className="orbit-group animate-[spin_20s_linear_infinite]" style={{ transformOrigin: "500px 500px" }}>
                        <circle cx="500" cy="500" r="190" stroke="currentColor" strokeWidth="1.5" fill="none" className="text-blue-400/20" />
                        <circle cx="690" cy="500" r="8" fill="currentColor" className="text-blue-500/80" />
                        <text x="690" y="530" textAnchor="middle" className="font-great-vibes text-xl fill-blue-300/60" style={{ fontFamily: 'var(--font-great-vibes)' }}>Terra</text>
                    </g>

                    {/* Mars */}
                    <g className="orbit-group animate-[spin_35s_linear_infinite]" style={{ transformOrigin: "500px 500px" }}>
                        <circle cx="500" cy="500" r="260" stroke="currentColor" strokeWidth="1" fill="none" className="text-red-900/40" />
                        <circle cx="240" cy="500" r="7" fill="currentColor" className="text-red-400/50" />
                        <text x="240" y="480" textAnchor="middle" className="font-great-vibes text-xl fill-red-300/30" style={{ fontFamily: 'var(--font-great-vibes)' }}>Martis</text>
                    </g>

                    {/* Jupiter */}
                    <g className="orbit-group animate-[spin_60s_linear_infinite]" style={{ transformOrigin: "500px 500px" }}>
                        <circle cx="500" cy="500" r="350" stroke="currentColor" strokeWidth="1" fill="none" className="text-orange-100/10" />
                        <circle cx="850" cy="500" r="18" fill="currentColor" className="text-slate-200/40" />
                        <text x="850" y="540" textAnchor="middle" className="font-great-vibes text-2xl fill-slate-400/30" style={{ fontFamily: 'var(--font-great-vibes)' }}>Iovis</text>
                    </g>

                    {/* Saturn */}
                    <g className="orbit-group animate-[spin_90s_linear_infinite]" style={{ transformOrigin: "500px 500px" }}>
                        <circle cx="500" cy="500" r="450" stroke="currentColor" strokeWidth="1" fill="none" className="text-cyan-100/10" />
                        <ellipse cx="50" cy="500" rx="20" ry="8" fill="none" stroke="currentColor" strokeWidth="2" className="text-cyan-200/20" transform="rotate(20 50 500)" />
                        <circle cx="50" cy="500" r="12" fill="currentColor" className="text-cyan-200/30" />
                        <text x="50" y="460" textAnchor="middle" className="font-great-vibes text-2xl fill-cyan-400/20" style={{ fontFamily: 'var(--font-great-vibes)' }}>Saturnus</text>
                    </g>

                    {/* Firmament of Fixed Stars */}
                    <circle cx="500" cy="500" r="490" stroke="currentColor" strokeWidth="2" fill="none" className="text-white/5" strokeDasharray="4 4" />
                    <path id="firmament-path" d="M 10,500 A 490,490 0 1,1 990,500 A 490,490 0 1,1 10,500" fill="none" />
                    <text className="font-great-vibes text-3xl fill-white/10 tracking-[1em] uppercase" style={{ fontFamily: 'var(--font-great-vibes)' }}>
                        <textPath href="#firmament-path" startOffset="50%" textAnchor="middle">Stellarum Fixarum Sphaera Immobilis</textPath>
                    </text>

                </svg>
            </div>
        </div>
    );
}
