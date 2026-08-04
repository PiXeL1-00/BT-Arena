"use client";

import ErrorBoundary from "@/components/ErrorBoundary";

export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    return (
        <html>
            <body className="bg-[#050510] text-white min-h-screen flex items-center justify-center p-4">
                <ErrorBoundary
                    error={error}
                    reset={reset}
                    title="Application Error"
                    className="max-w-2xl w-full"
                />
            </body>
        </html>
    );
}
