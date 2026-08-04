"use client";

import ErrorBoundary from "@/components/ErrorBoundary";

export default function RunError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    return (
        <div className="container mx-auto px-4 py-8 max-w-7xl min-h-[calc(100vh-80px)] flex items-center justify-center">
            <ErrorBoundary
                error={error}
                reset={reset}
                title="Run Dashboard Error"
                className="w-full max-w-2xl"
            />
        </div>
    );
}
