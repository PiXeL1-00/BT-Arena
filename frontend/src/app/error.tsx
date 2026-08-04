"use client";

import ErrorBoundary from "@/components/ErrorBoundary";

export default function ErrorPage({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    return (
        <div className="container mx-auto px-4 py-8 max-w-7xl">
            <ErrorBoundary error={error} reset={reset} title="Page Error" />
        </div>
    );
}
