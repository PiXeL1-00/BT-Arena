"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { ArrowUpRight, BarChart3, Info, Menu, Rocket, Workflow, X } from "lucide-react";
import { useNavLock } from "@/hooks/useNavLock";

export function GlobalHeader() {
    const { locked } = useNavLock();
    const [drawerOpen, setDrawerOpen] = useState(false);

    const disabledClass = "pointer-events-none opacity-40 cursor-not-allowed";

    const closeDrawer = useCallback(() => setDrawerOpen(false), []);

    // Close drawer on escape key
    useEffect(() => {
        if (!drawerOpen) return;
        const onKey = (e: KeyboardEvent) => {
            if (e.key === "Escape") closeDrawer();
        };
        document.addEventListener("keydown", onKey);
        document.body.style.overflow = "hidden";
        return () => {
            document.removeEventListener("keydown", onKey);
            document.body.style.overflow = "";
        };
    }, [drawerOpen, closeDrawer]);

    const navLinks = (
        <>
            <Link
                href="/methodology"
                className={`group relative flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-lg border border-[#292524]/10 bg-[#FFFFFF]/80 backdrop-blur-sm text-[#292524]/70 hover:text-[#412AD1] hover:border-[#412AD1]/30 hover:bg-[#412AD1]/5 transition-all duration-300 ${locked ? disabledClass : ""}`}
                aria-disabled={locked}
                tabIndex={locked ? -1 : undefined}
                onClick={locked ? (e) => e.preventDefault() : undefined}
            >
                <Workflow className="w-3 h-3 text-[#412AD1]" />
                <span className="tracking-wide">Methodology</span>
            </Link>
        </>
    );

    const navActions = (
        <>
            <Link
                href="/about"
                className={`group flex items-center gap-1.5 text-sm font-medium px-4 py-1.5 rounded-xl border border-[#292524]/10 bg-[#FFFFFF]/80 backdrop-blur-sm text-[#292524]/70 hover:text-[#412AD1] hover:border-[#412AD1]/30 hover:bg-[#412AD1]/5 transition-all duration-300 ${locked ? disabledClass : ""}`}
                aria-disabled={locked}
                tabIndex={locked ? -1 : undefined}
                onClick={locked ? (e) => e.preventDefault() : undefined}
            >
                <Info className="w-3.5 h-3.5 text-[#412AD1]" />
                <span className="tracking-wide">About</span>
            </Link>
            <Link
                href="/graphs"
                className={`group flex items-center gap-1.5 text-sm font-medium px-4 py-1.5 rounded-xl border border-[#292524]/10 bg-[#FFFFFF]/80 backdrop-blur-sm text-[#292524]/70 hover:text-[#412AD1] hover:border-[#412AD1]/30 hover:bg-[#412AD1]/5 transition-all duration-300 ${locked ? disabledClass : ""}`}
                aria-disabled={locked}
                tabIndex={locked ? -1 : undefined}
                onClick={locked ? (e) => e.preventDefault() : undefined}
            >
                <BarChart3 className="w-3.5 h-3.5 text-[#412AD1]" />
                <span className="tracking-wide">Analytics</span>
            </Link>
            <Link
                href="/datasets"
                className={`group flex items-center gap-2 text-sm sm:text-base font-semibold px-5 sm:px-6 py-2 sm:py-2.5 rounded-xl bg-[#412AD1] text-[#FFFFFF] shadow-lg shadow-[#412AD1]/20 hover:bg-[#412AD1]/90 hover:-translate-y-0.5 transition-all duration-300 ${locked ? disabledClass : ""}`}
                aria-disabled={locked}
                tabIndex={locked ? -1 : undefined}
                onClick={locked ? (e) => e.preventDefault() : undefined}
            >
                <Rocket className="w-4 h-4 sm:w-[18px] sm:h-[18px]" />
                <span className="tracking-wide">Get Started</span>
                <ArrowUpRight className="w-3.5 h-3.5 sm:w-4 sm:h-4 opacity-70 group-hover:opacity-100 transition-opacity" />
            </Link>
        </>
    );

    return (
        <>
            <div className="flex w-full gap-3 sm:gap-6 px-4 sm:px-6 lg:px-8 pt-3 sm:pt-[14px] absolute top-0 left-0 z-50 pointer-events-none">
                <div className="flex-1 flex items-start gap-4 pointer-events-auto">
                    {/* Title + sub-links (always visible) */}
                    <div className="flex flex-col items-start gap-1">
                        <Link
                            href="/"
                            className={`block text-xl sm:text-3xl lg:text-4xl font-extrabold leading-tight text-[#292524] mb-0 hover:text-[#412AD1] transition-colors cursor-pointer w-fit tracking-tight ${locked ? disabledClass : ""}`}
                            aria-disabled={locked}
                            tabIndex={locked ? -1 : undefined}
                            onClick={locked ? (e) => e.preventDefault() : undefined}
                        >
                            Bittensor <span className="font-serif italic font-normal text-[#412AD1]">Arena</span>
                        </Link>
                        {/* Sub-links: hidden on mobile, visible on sm+ */}
                        <div className="hidden sm:flex items-center gap-2">
                            {navLinks}
                        </div>
                    </div>

                    {/* Desktop nav actions: hidden on mobile */}
                    <div className="hidden md:flex items-center gap-3">
                        {navActions}
                    </div>

                    {/* Hamburger button: visible on mobile only */}
                    <button
                        className="md:hidden ml-auto p-2 rounded-xl border border-[#292524]/10 bg-[#FFFFFF]/80 backdrop-blur-sm text-[#292524]/70 hover:text-[#412AD1] hover:border-[#412AD1]/30 transition-all duration-300 tap-target"
                        onClick={() => setDrawerOpen(true)}
                        aria-label="Open menu"
                    >
                        <Menu className="w-5 h-5" />
                    </button>
                </div>
            </div>

            {/* Mobile Drawer Overlay */}
            {drawerOpen && (
                <div className="fixed inset-0 z-[100] md:hidden" onClick={closeDrawer}>
                    {/* Backdrop */}
                    <div className="absolute inset-0 bg-[#0C0A09]/40 backdrop-blur-sm animate-[fadeIn_200ms_ease-out]" />

                    {/* Drawer Panel */}
                    <div
                        className="absolute top-0 right-0 h-full w-[280px] max-w-[85vw] bg-[#FFFFFF] backdrop-blur-xl border-l border-[#292524]/10 shadow-[-8px_0_32px_rgba(12,10,9,0.1)] flex flex-col animate-[slideInRight_250ms_ease-out]"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Drawer Header */}
                        <div className="flex items-center justify-between px-5 pt-4 pb-3 border-b border-[#292524]/10">
                            <span className="text-sm font-semibold text-[#292524]/70 tracking-wide">Menu</span>
                            <button
                                onClick={closeDrawer}
                                className="p-2 rounded-lg text-[#292524]/50 hover:text-[#292524] hover:bg-[#292524]/5 transition-all tap-target"
                                aria-label="Close menu"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Drawer Nav Links */}
                        <nav className="flex flex-col gap-1 p-4" onClick={closeDrawer}>
                            <Link
                                href="/methodology"
                                className="flex items-center gap-3 px-4 py-3 rounded-xl text-[#292524]/70 hover:text-[#412AD1] hover:bg-[#412AD1]/5 transition-all tap-target"
                            >
                                <Workflow className="w-4 h-4 text-[#412AD1]" />
                                <span className="text-sm font-medium tracking-wide">Methodology</span>
                            </Link>
                            <Link
                                href="/about"
                                className="flex items-center gap-3 px-4 py-3 rounded-xl text-[#292524]/70 hover:text-[#412AD1] hover:bg-[#412AD1]/5 transition-all tap-target"
                            >
                                <Info className="w-4 h-4 text-[#412AD1]" />
                                <span className="text-sm font-medium tracking-wide">About</span>
                            </Link>
                            <Link
                                href="/graphs"
                                className="flex items-center gap-3 px-4 py-3 rounded-xl text-[#292524]/70 hover:text-[#412AD1] hover:bg-[#412AD1]/5 transition-all tap-target"
                            >
                                <BarChart3 className="w-4 h-4 text-[#412AD1]" />
                                <span className="text-sm font-medium tracking-wide">Analytics</span>
                            </Link>

                            <div className="my-2 h-px bg-[#292524]/10" />

                            <Link
                                href="/datasets"
                                className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-[#412AD1] text-[#FFFFFF] font-semibold shadow-lg shadow-[#412AD1]/20 tap-target"
                            >
                                <Rocket className="w-4 h-4" />
                                <span className="tracking-wide">Get Started</span>
                                <ArrowUpRight className="w-4 h-4 opacity-70" />
                            </Link>
                        </nav>
                    </div>
                </div>
            )}
        </>
    );
}
