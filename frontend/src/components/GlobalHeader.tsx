"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { ArrowUpRight, BarChart3, ExternalLink, Info, Menu, Rocket, Workflow, X } from "lucide-react";
import { useNavLock } from "@/hooks/useNavLock";

export function GlobalHeader() {
    const { locked } = useNavLock();
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [visible, setVisible] = useState(true);
    const prevScrollY = useRef(0);

    const disabledClass = "pointer-events-none opacity-40 cursor-not-allowed";

    const closeDrawer = useCallback(() => setDrawerOpen(false), []);

    // Smart navbar: always visible at top, hides when scrolling DOWN, reappears on scroll UP
    useEffect(() => {
        const handleScroll = () => {
            const currentScrollY = window.scrollY || document.documentElement.scrollTop;

            if (currentScrollY <= 20) {
                // At very top — always show
                setVisible(true);
            } else if (currentScrollY < prevScrollY.current) {
                // Scrolled UP → reveal navbar
                setVisible(true);
            } else if (currentScrollY > prevScrollY.current + 5) {
                // Scrolled DOWN (5px threshold to avoid jitter) → hide navbar
                setVisible(false);
            }

            prevScrollY.current = currentScrollY;
        };

        window.addEventListener("scroll", handleScroll, { passive: true });
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

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
                href="/methodology"
                className={`group flex items-center gap-1.5 text-sm font-medium px-4 py-1.5 rounded-xl border border-[#292524]/10 bg-[#FFFFFF]/80 backdrop-blur-sm text-[#292524]/70 hover:text-[#412AD1] hover:border-[#412AD1]/30 hover:bg-[#412AD1]/5 transition-all duration-300 ${locked ? disabledClass : ""}`}
                aria-disabled={locked}
                tabIndex={locked ? -1 : undefined}
                onClick={locked ? (e) => e.preventDefault() : undefined}
            >
                <Workflow className="w-3.5 h-3.5 text-[#412AD1]" />
                <span className="tracking-wide">Methodology</span>
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
                className={`group flex items-center gap-2 text-sm font-semibold px-5 py-1.5 rounded-xl bg-[#412AD1] text-[#FFFFFF] shadow-lg shadow-[#412AD1]/20 hover:bg-[#412AD1]/90 hover:-translate-y-0.5 transition-all duration-300 ${locked ? disabledClass : ""}`}
                aria-disabled={locked}
                tabIndex={locked ? -1 : undefined}
                onClick={locked ? (e) => e.preventDefault() : undefined}
            >
                <Rocket className="w-4 h-4" />
                <span className="tracking-wide">Get Started</span>
                <ArrowUpRight className="w-3.5 h-3.5 opacity-70 group-hover:opacity-100 transition-opacity" />
            </Link>
            <a
                href="https://taostats.io/subnets/104"
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center gap-1.5 text-sm font-medium px-4 py-1.5 rounded-xl border border-[#292524]/10 bg-[#FFFFFF]/80 backdrop-blur-sm text-[#292524]/70 hover:text-[#412AD1] hover:border-[#412AD1]/30 hover:bg-[#412AD1]/5 transition-all duration-300"
            >
                <span className="text-[#29BC41] font-semibold">Powered by</span>
                <span className="tracking-wide">Masxai</span>
                <span className="text-[#412AD1] font-semibold">SN104</span>
                <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 transition-opacity ml-0.5" />
            </a>
        </>
    );

    return (
        <>
            <header
                className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ease-in-out border-b border-[#292524]/10 bg-[#FFFFFF]/90 backdrop-blur-md shadow-sm ${
                    visible || drawerOpen
                        ? "translate-y-0 opacity-100 pointer-events-auto"
                        : "-translate-y-full opacity-0 pointer-events-none"
                }`}
            >
                <div className="relative flex items-center justify-center px-4 sm:px-6 lg:px-8 py-3">

                    {/* LOGO — LEFT */}
                    <Link
                        href="/"
                        className={`absolute left-4 sm:left-6 lg:left-8 text-xl sm:text-2xl lg:text-3xl font-extrabold text-[#292524] hover:text-[#412AD1] transition-colors cursor-pointer tracking-tight ${
                            locked ? disabledClass : ""
                        }`}
                        aria-disabled={locked}
                        tabIndex={locked ? -1 : undefined}
                        onClick={locked ? (e) => e.preventDefault() : undefined}
                    >
                        Bittensor{" "}
                        <span className="font-serif italic font-normal text-[#412AD1]">
                            Arena
                        </span>
                    </Link>

                    {/* NAV — TRUE CENTER */}
                    <div className="hidden md:flex items-center justify-center gap-2.5 sm:gap-3">
                        {navLinks}
                    </div>

                    {/* MOBILE HAMBURGER */}
                    <button
                        className="absolute right-4 sm:right-6 md:hidden p-2 rounded-xl border border-[#292524]/10 bg-[#FFFFFF]/80 backdrop-blur-sm text-[#292524]/70 hover:text-[#412AD1] hover:border-[#412AD1]/30 transition-all duration-300 tap-target"
                        onClick={() => setDrawerOpen(true)}
                        aria-label="Open menu"
                    >
                        <Menu className="w-5 h-5" />
                    </button>

                </div>
            </header>

            {/* Mobile Drawer Overlay */}
            {drawerOpen && (
                <div className="fixed inset-0 z-[100] md:hidden" onClick={closeDrawer}>
                    {/* Backdrop */}
                    <div className="absolute inset-0 bg-[#0C0A09]/40 backdrop-blur-sm animate-[fadeIn_200ms_ease-out]" />

                    {/* Drawer Panel */}
                    <div
                        className="absolute top-0 right-0 h-full w-[290px] max-w-[85vw] bg-[#FFFFFF] backdrop-blur-xl border-l border-[#292524]/10 shadow-[-8px_0_32px_rgba(12,10,9,0.1)] flex flex-col animate-[slideInRight_250ms_ease-out]"
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
                        <nav className="flex flex-col gap-2 p-4" onClick={closeDrawer}>
                            <Link
                                href="/methodology"
                                className="flex items-center gap-3 px-4 py-3 rounded-xl border border-[#292524]/10 text-[#292524]/70 hover:text-[#412AD1] hover:bg-[#412AD1]/5 transition-all tap-target text-sm font-medium"
                            >
                                <Workflow className="w-4 h-4 text-[#412AD1]" />
                                <span className="tracking-wide">Methodology</span>
                            </Link>
                            <a
                                href="https://taostats.io/subnets/104"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 px-4 py-3 rounded-xl border border-[#292524]/10 text-[#292524]/70 hover:text-[#412AD1] hover:bg-[#412AD1]/5 transition-all tap-target text-sm font-medium"
                            >
                                <span className="text-[#29BC41] font-semibold">Powered by</span>
                                <span className="tracking-wide">Masxai</span>
                                <span className="text-[#412AD1] font-semibold">SN104</span>
                                <ExternalLink className="w-3.5 h-3.5 opacity-60 ml-auto" />
                            </a>
                            <Link
                                href="/about"
                                className="flex items-center gap-3 px-4 py-3 rounded-xl border border-[#292524]/10 text-[#292524]/70 hover:text-[#412AD1] hover:bg-[#412AD1]/5 transition-all tap-target text-sm font-medium"
                            >
                                <Info className="w-4 h-4 text-[#412AD1]" />
                                <span className="tracking-wide">About</span>
                            </Link>
                            <Link
                                href="/graphs"
                                className="flex items-center gap-3 px-4 py-3 rounded-xl border border-[#292524]/10 text-[#292524]/70 hover:text-[#412AD1] hover:bg-[#412AD1]/5 transition-all tap-target text-sm font-medium"
                            >
                                <BarChart3 className="w-4 h-4 text-[#412AD1]" />
                                <span className="tracking-wide">Analytics</span>
                            </Link>

                            <div className="my-2 h-px bg-[#292524]/10" />

                            <Link
                                href="/datasets"
                                className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-[#412AD1] text-[#FFFFFF] font-semibold shadow-lg shadow-[#412AD1]/20 tap-target text-sm"
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

