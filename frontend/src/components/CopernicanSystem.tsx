"use client";

import { useEffect, useState } from "react";

export default function CopernicanSystem() {
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) return null;

    return (
        <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none select-none">
            <div className="absolute inset-0 bg-gradient-to-b from-[#412AD1]/[0.02] via-background to-background" />
            <div className="absolute w-[900px] h-[900px] rounded-full bg-[#412AD1]/[0.03] blur-[140px] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
            <div className="absolute w-[600px] h-[600px] rounded-full bg-[#B50BBB]/[0.02] blur-[120px] top-1/3 left-1/3 -translate-x-1/2 -translate-y-1/2" />
        </div>
    );
}

