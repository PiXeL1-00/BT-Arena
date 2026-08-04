"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
    error: Error & { digest?: string };
    reset: () => void;
    title?: string;
    className?: string;
}

export default function ErrorBoundary({ error, reset, title = "Something went wrong!", className = "" }: Props) {
    useEffect(() => {
        // Log the error to an error reporting service
        console.error("ErrorBoundary caught error:", error);
    }, [error]);

    return (
        <div className={`flex flex-col items-center justify-center min-h-[400px] p-8 text-center glass-panel rounded-3xl ${className}`}>
            <div className="bg-red-500/10 p-4 rounded-full mb-6 border border-red-500/20 shadow-[0_0_30px_rgba(239,68,68,0.2)]">
                <AlertTriangle className="w-12 h-12 text-red-500" />
            </div>

            <h2 className="text-2xl font-light text-white mb-2">{title}</h2>

            <div className="max-w-md w-full glass-button p-4 rounded-xl mb-8 overflow-hidden">
                <p className="text-red-300/80 font-mono text-xs break-all">
                    {error.message || "Unknown error occurred"}
                </p>
                {error.digest && (
                    <p className="text-white/30 text-[10px] mt-2 font-mono">
                        Digest: {error.digest}
                    </p>
                )}
            </div>

            <button
                onClick={reset}
                className="group relative px-6 py-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all active:scale-95 flex items-center gap-2"
            >
                <RefreshCw className="w-4 h-4 text-cyan-400 group-hover:rotate-180 transition-transform duration-500" />
                <span className="text-sm font-medium text-white/90 group-hover:text-white">
                    Try again
                </span>
            </button>
        </div>
    );
}
