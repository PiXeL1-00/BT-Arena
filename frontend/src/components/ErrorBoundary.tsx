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
            <div className="bg-[#B50BBB]/10 p-4 rounded-full mb-6 border border-[#B50BBB]/20 shadow-[0_0_30px_rgba(181,11,187,0.15)]">
                <AlertTriangle className="w-12 h-12 text-[#B50BBB]" />
            </div>

            <h2 className="text-2xl font-light text-[#292524] mb-2">{title}</h2>

            <div className="max-w-md w-full glass-button p-4 rounded-xl mb-8 overflow-hidden">
                <p className="text-[#B50BBB]/80 font-mono text-xs break-all">
                    {error.message || "Unknown error occurred"}
                </p>
                {error.digest && (
                    <p className="text-[#292524]/40 text-[10px] mt-2 font-mono">
                        Digest: {error.digest}
                    </p>
                )}
            </div>

            <button
                onClick={reset}
                className="group relative px-6 py-3 bg-[#FFFFFF] border border-[#292524]/10 rounded-xl hover:bg-[#412AD1]/5 transition-all active:scale-95 flex items-center gap-2"
            >
                <RefreshCw className="w-4 h-4 text-[#412AD1] group-hover:rotate-180 transition-transform duration-500" />
                <span className="text-sm font-medium text-[#292524] group-hover:text-[#412AD1]">
                    Try again
                </span>
            </button>
        </div>
    );
}
