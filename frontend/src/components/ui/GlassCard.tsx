"use client";

import { useState, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { Maximize2, Minimize2 } from "lucide-react";

interface GlassCardProps {
    children: React.ReactNode;
    title?: string;
    className?: string;
    size?: "sm" | "md" | "lg";
    expandable?: boolean;
}

const SIZE_CONFIG = {
    sm: { padding: "p-3", titleText: "text-[9px]", mb: "mb-1.5", gap: "gap-1", dot: "w-1 h-1" },
    md: { padding: "p-5", titleText: "text-[10px]", mb: "mb-3", gap: "gap-1.5", dot: "w-1.5 h-1.5" },
    lg: { padding: "p-6", titleText: "text-xs", mb: "mb-4", gap: "gap-2", dot: "w-1.5 h-1.5" },
} as const;

export function GlassCard({ children, title, className = "", size = "md", expandable = false }: GlassCardProps) {
    const cfg = SIZE_CONFIG[size];
    const [expanded, setExpanded] = useState(false);

    const close = useCallback(() => setExpanded(false), []);

    useEffect(() => {
        if (!expanded) return;
        const onKey = (e: KeyboardEvent) => {
            if (e.key === "Escape") close();
        };
        document.addEventListener("keydown", onKey);
        document.body.style.overflow = "hidden";
        return () => {
            document.removeEventListener("keydown", onKey);
            document.body.style.overflow = "";
        };
    }, [expanded, close]);

    const header = title ? (
        <h3 className={`${expanded ? "text-xs" : cfg.titleText} font-semibold text-[#292524]/60 uppercase tracking-[0.15em] ${expanded ? "mb-4" : cfg.mb} flex items-center ${cfg.gap} flex-shrink-0`}>
            <span className={`${cfg.dot} rounded-full bg-[#412AD1]`} />
            {title}
            {expandable && (
                <button
                    onClick={(e) => { e.stopPropagation(); setExpanded((v) => !v); }}
                    className="ml-auto p-1 rounded-md text-[#292524]/40 hover:text-[#412AD1] hover:bg-[#292524]/5 transition-all duration-200"
                    aria-label={expanded ? "Minimize" : "Maximize"}
                >
                    {expanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                </button>
            )}
        </h3>
    ) : null;

    const overlay = expanded
        ? createPortal(
            <div
                className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 animate-[fadeIn_200ms_ease-out]"
                onClick={close}
            >
                <div className="absolute inset-0 bg-[#0C0A09]/50 backdrop-blur-md" />
                <div
                    className="relative w-full h-full max-w-[95vw] max-h-[92vh] bg-[#FFFFFF]/95 backdrop-blur-xl rounded-2xl border border-[#292524]/15 p-4 sm:p-8 shadow-[0_8px_64px_rgba(12,10,9,0.15)] flex flex-col animate-[scaleIn_200ms_ease-out]"
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className="absolute top-0 left-8 right-8 h-px bg-gradient-to-r from-transparent via-[#412AD1]/30 to-transparent" />
                    {header}
                    <div className="flex-1 min-h-0 glass-expanded">{children}</div>
                </div>
            </div>,
            document.body,
        )
        : null;

    return (
        <>
            <div className={`relative group rounded-2xl overflow-hidden ${className}`}>
                <div className="absolute top-0 left-4 right-4 h-px bg-gradient-to-r from-transparent via-[#412AD1]/25 to-transparent group-hover:via-[#412AD1]/50 transition-colors duration-500" />
                <div className={`relative bg-[#FFFFFF]/85 backdrop-blur-xl rounded-2xl border border-[#292524]/10 ${cfg.padding} shadow-[0_2px_8px_rgba(12,10,9,0.04)] group-hover:shadow-[0_8px_24px_rgba(12,10,9,0.08)] group-hover:-translate-y-0.5 transition-all duration-300 h-full flex flex-col`}>
                    {header}
                    <div className="flex-1 min-h-0">{children}</div>
                </div>
            </div>
            {overlay}
        </>
    );
}
