interface RubricBarProps {
    label: string;
    range: string;
    width: string;
    gradient: string;
    description: string;
}

export function RubricBar({ label, range, width, gradient, description }: RubricBarProps) {
    return (
        <div className="space-y-1.5 group">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-foreground">{label}</span>
                    <span className="text-xs text-muted-foreground font-mono">{range}</span>
                </div>
            </div>
            <div className="h-7 rounded-md bg-white/[0.04] overflow-hidden">
                <div
                    className="h-full rounded-md transition-all duration-700 group-hover:brightness-110"
                    style={{ width, background: gradient }}
                />
            </div>
            <p className="text-xs text-muted-foreground/80 leading-relaxed">{description}</p>
        </div>
    );
}
