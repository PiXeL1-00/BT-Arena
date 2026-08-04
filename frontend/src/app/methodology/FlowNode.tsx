import type { LucideIcon } from "lucide-react";

interface FlowNodeProps {
    icon: LucideIcon;
    title: string;
    description: string;
    accentColor: string;
}

export function FlowNode({ icon: Icon, title, description, accentColor }: FlowNodeProps) {
    return (
        <div className="glass-card p-4 sm:p-5 flex flex-col items-center text-center gap-2 min-w-[140px] max-w-[180px] group hover:scale-[1.03] transition-transform duration-300">
            <div
                className="p-2.5 rounded-xl"
                style={{ background: `${accentColor}15`, color: accentColor }}
            >
                <Icon className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-foreground">{title}</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
        </div>
    );
}
