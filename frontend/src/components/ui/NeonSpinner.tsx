"use client";

interface Props {
    className?: string;
}

export function NeonSpinner({ className = "" }: Props) {
    return (
        <div className={`flex items-center justify-center gap-1.5 ${className}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400/80 animate-[pulse-dot_1.4s_ease-in-out_infinite]" />
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400/60 animate-[pulse-dot_1.4s_ease-in-out_0.2s_infinite]" />
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400/40 animate-[pulse-dot_1.4s_ease-in-out_0.4s_infinite]" />
            <style>{`
                @keyframes pulse-dot {
                    0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
                    40% { transform: scale(1.2); opacity: 1; }
                }
            `}</style>
        </div>
    );
}
