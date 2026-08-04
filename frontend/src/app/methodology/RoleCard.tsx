interface RoleCardProps {
    role: string;
    emoji: string;
    color: string;
    description: string;
    stance: string;
}

export function RoleCard({ role, emoji, color, description, stance }: RoleCardProps) {
    return (
        <div className="glass-card p-5 space-y-3 hover:scale-[1.02] transition-transform duration-300">
            <div className="flex items-center gap-3">
                <span className="text-2xl">{emoji}</span>
                <div>
                    <h3 className="text-sm font-bold text-foreground">{role}</h3>
                    <span
                        className="text-xs font-medium px-2 py-0.5 rounded-full"
                        style={{ background: `${color}20`, color }}
                    >
                        {stance}
                    </span>
                </div>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
        </div>
    );
}
