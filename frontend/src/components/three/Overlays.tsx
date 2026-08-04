"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import * as THREE from "three";

/* ═══════════════════ Legend Overlay ═══════════════════ */

interface LegendItem {
    label: string;
    color: string;
    value?: string;
}

interface LegendOverlayProps {
    items: LegendItem[];
    axes?: { x?: string; y?: string; z?: string };
    title?: string;
}

export function LegendOverlay({ items, axes, title }: LegendOverlayProps) {
    return (
        <div className="absolute inset-0 pointer-events-none z-10">
            {/* Legend box — bottom-left */}
            <div className="absolute bottom-3 left-3 pointer-events-auto">
                <div className="bg-black/70 backdrop-blur-md border border-white/10 rounded-xl px-3 py-2.5 max-w-[200px]">
                    {title && (
                        <div className="text-[9px] text-white/40 uppercase tracking-widest mb-1.5 font-semibold">
                            {title}
                        </div>
                    )}
                    <div className="space-y-1">
                        {items.map((item, i) => (
                            <div key={i} className="flex items-center gap-2 min-w-0">
                                <span
                                    className="w-2.5 h-2.5 rounded-full flex-shrink-0 shadow-[0_0_6px_currentColor]"
                                    style={{ backgroundColor: item.color, color: item.color }}
                                />
                                <span className="text-[10px] text-white/70 truncate leading-tight">
                                    {item.label}
                                </span>
                                {item.value && (
                                    <span className="text-[9px] text-white/40 ml-auto font-mono flex-shrink-0">
                                        {item.value}
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Axis labels — bottom-right */}
            {axes && (
                <div className="absolute bottom-3 right-3 pointer-events-auto">
                    <div className="bg-black/70 backdrop-blur-md border border-white/10 rounded-xl px-3 py-2 space-y-0.5">
                        <div className="text-[9px] text-white/40 uppercase tracking-widest mb-1 font-semibold">
                            Axes
                        </div>
                        {axes.x && (
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] text-cyan-400 font-bold w-3">X</span>
                                <span className="text-[10px] text-white/60">{axes.x}</span>
                            </div>
                        )}
                        {axes.y && (
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] text-amber-400 font-bold w-3">Y</span>
                                <span className="text-[10px] text-white/60">{axes.y}</span>
                            </div>
                        )}
                        {axes.z && (
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] text-emerald-400 font-bold w-3">Z</span>
                                <span className="text-[10px] text-white/60">{axes.z}</span>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

/* ═══════════════════ Hover Tooltip ═══════════════════ */

export interface TooltipData {
    x: number;
    y: number;
    label: string;
    rows: { key: string; value: string }[];
}

interface TooltipOverlayProps {
    data: TooltipData | null;
}

export function TooltipOverlay({ data }: TooltipOverlayProps) {
    if (!data) return null;
    return (
        <div
            className="absolute z-20 pointer-events-none"
            style={{ left: data.x + 12, top: data.y - 10 }}
        >
            <div className="bg-black/85 backdrop-blur-lg border border-cyan-400/30 rounded-lg px-3 py-2 shadow-[0_0_20px_rgba(34,211,238,0.15)]">
                <div className="text-[11px] text-cyan-300 font-semibold mb-1">{data.label}</div>
                {data.rows.map((r, i) => (
                    <div key={i} className="flex justify-between gap-4">
                        <span className="text-[10px] text-white/50">{r.key}</span>
                        <span className="text-[10px] text-white/90 font-mono">{r.value}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

/* ═══════════════════ Dimension Legend ═══════════════════ */

interface DimensionLegendProps {
    dimensions: { label: string; color: string }[];
    title?: string;
}

export function DimensionLegend({ dimensions, title }: DimensionLegendProps) {
    return (
        <div className="absolute top-3 right-3 pointer-events-auto z-10">
            <div className="bg-black/70 backdrop-blur-md border border-white/10 rounded-xl px-3 py-2">
                {title && (
                    <div className="text-[9px] text-white/40 uppercase tracking-widest mb-1.5 font-semibold">
                        {title}
                    </div>
                )}
                <div className="flex flex-wrap gap-x-3 gap-y-1">
                    {dimensions.map((d, i) => (
                        <div key={i} className="flex items-center gap-1.5">
                            <span
                                className="w-2 h-2 rounded-sm flex-shrink-0"
                                style={{ backgroundColor: d.color }}
                            />
                            <span className="text-[10px] text-white/60">{d.label}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

/* ═══════════════════ Mouse Hover Hook ═══════════════════ */

export function useHoverRaycast(
    containerRef: React.RefObject<HTMLDivElement | null>,
    cameraRef: React.RefObject<THREE.PerspectiveCamera | null>,
    targetsRef: React.RefObject<THREE.Object3D[]>,
) {
    const [tooltip, setTooltip] = useState<TooltipData | null>(null);
    const raycaster = useRef(new THREE.Raycaster());
    const mouse = useRef(new THREE.Vector2());

    const onMove = useCallback(
        (e: MouseEvent) => {
            const el = containerRef.current;
            const cam = cameraRef.current;
            const targets = targetsRef.current;
            if (!el || !cam || !targets?.length) return;

            const rect = el.getBoundingClientRect();
            mouse.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

            raycaster.current.setFromCamera(mouse.current, cam);
            const hits = raycaster.current.intersectObjects(targets, false);

            if (hits.length > 0) {
                const obj = hits[0].object;
                const ud = obj.userData as {
                    tooltipLabel?: string;
                    tooltipRows?: { key: string; value: string }[];
                };
                if (ud.tooltipLabel) {
                    setTooltip({
                        x: e.clientX - rect.left,
                        y: e.clientY - rect.top,
                        label: ud.tooltipLabel,
                        rows: ud.tooltipRows ?? [],
                    });
                    return;
                }
            }
            setTooltip(null);
        },
        [containerRef, cameraRef, targetsRef],
    );

    const onLeave = useCallback(() => setTooltip(null), []);

    useEffect(() => {
        const el = containerRef.current;
        if (!el) return;
        el.addEventListener("mousemove", onMove);
        el.addEventListener("mouseleave", onLeave);
        return () => {
            el.removeEventListener("mousemove", onMove);
            el.removeEventListener("mouseleave", onLeave);
        };
    }, [containerRef, onMove, onLeave]);

    return tooltip;
}
