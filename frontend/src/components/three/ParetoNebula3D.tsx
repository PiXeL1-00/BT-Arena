"use client";

import { useCallback, useMemo, useRef } from "react";
import * as THREE from "three";
import Scene3D, { type SceneApi } from "./Scene3D";
import { LegendOverlay, TooltipOverlay, useHoverRaycast } from "./Overlays";
import type { ParetoItem } from "@/lib/galileoTypes";

/* ───── distinct color per model (by index) ───── */
const MODEL_COLORS: { hex: number; css: string }[] = [
    { hex: 0x22d3ee, css: "#22d3ee" },  // cyan
    { hex: 0xf59e0b, css: "#f59e0b" },  // amber
    { hex: 0x34d399, css: "#34d399" },  // emerald
    { hex: 0xf43f5e, css: "#f43f5e" },  // rose
    { hex: 0xa78bfa, css: "#a78bfa" },  // violet
    { hex: 0xfb923c, css: "#fb923c" },  // orange
    { hex: 0x67e8f9, css: "#67e8f9" },  // light-cyan
    { hex: 0x818cf8, css: "#818cf8" },  // indigo
];

interface Props {
    items: ParetoItem[];
    modelNames: Map<string, string>;
}

export default function ParetoNebula3D({ items, modelNames }: Props) {
    const containerRef = useRef<HTMLDivElement>(null);
    const cameraRef = useRef<THREE.PerspectiveCamera>(null);
    const targetsRef = useRef<THREE.Object3D[]>([]);

    const tooltip = useHoverRaycast(containerRef, cameraRef, targetsRef);

    /* ── normalize data for spatial mapping ── */
    const normalized = useMemo(() => {
        if (!items.length) return [];
        const scores = items.map((p) => p.avg_score ?? 0);
        const latencies = items.map((p) => Math.log10(Math.max(p.avg_latency_ms ?? 1, 1)));
        const costs = items.map((p) => p.avg_cost_usd ?? 0);

        const range = (arr: number[]) => {
            const min = Math.min(...arr);
            const max = Math.max(...arr);
            return { min, max, span: max - min || 1 };
        };
        const sR = range(scores);
        const lR = range(latencies);
        const cR = range(costs);

        const SCALE = 6;
        return items.map((p, i) => ({
            item: p,
            x: ((scores[i] - sR.min) / sR.span - 0.5) * SCALE,
            y: ((latencies[i] - lR.min) / lR.span - 0.5) * SCALE,
            z: ((costs[i] - cR.min) / cR.span - 0.5) * SCALE,
            radius: 0.15 + Math.sqrt(p.n) * 0.04,
            color: MODEL_COLORS[i % MODEL_COLORS.length],
            name: modelNames.get(p.llm_id) ?? p.llm_id.slice(0, 15),
        }));
    }, [items, modelNames]);

    /* ── legend items ── */
    const legendItems = useMemo(
        () =>
            normalized.map((d) => ({
                label: d.name,
                color: d.color.css,
                value: `${(d.item.avg_score ?? 0).toFixed(1)}`,
            })),
        [normalized],
    );

    const onInit = useCallback(
        (api: SceneApi) => {
            const { scene, disposables } = api;

            /* ── axis lines with labels ── */
            const createAxisLine = (from: THREE.Vector3, to: THREE.Vector3, color: number) => {
                const points = [from, to];
                const geo = new THREE.BufferGeometry().setFromPoints(points);
                const mat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.45, linewidth: 2 });
                const line = new THREE.Line(geo, mat);
                scene.add(line);
                disposables.add(geo);
                disposables.add(mat);
            };

            const createAxisLabel = (text: string, position: THREE.Vector3, color: string) => {
                const canvas = document.createElement("canvas");
                const ctx = canvas.getContext("2d")!;
                canvas.width = 256;
                canvas.height = 64;
                ctx.font = "bold 28px ui-monospace, 'SF Mono', monospace";
                ctx.fillStyle = color;
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(text, 128, 32);
                const tex = new THREE.CanvasTexture(canvas);
                tex.needsUpdate = true;
                const spriteMat = new THREE.SpriteMaterial({
                    map: tex,
                    transparent: true,
                    depthTest: false,
                });
                const sprite = new THREE.Sprite(spriteMat);
                sprite.position.copy(position);
                sprite.scale.set(2.8, 0.7, 1);
                scene.add(sprite);
                disposables.add(tex);
                disposables.add(spriteMat);
            };

            createAxisLine(new THREE.Vector3(-4, -3, -4), new THREE.Vector3(4, -3, -4), 0x22d3ee);
            createAxisLine(new THREE.Vector3(-4, -3, -4), new THREE.Vector3(-4, 4, -4), 0xf59e0b);
            createAxisLine(new THREE.Vector3(-4, -3, -4), new THREE.Vector3(-4, -3, 4), 0x34d399);

            createAxisLabel("Score →", new THREE.Vector3(4.8, -3, -4), "#22d3ee");
            createAxisLabel("Latency →", new THREE.Vector3(-4, 4.6, -4), "#f59e0b");
            createAxisLabel("Cost →", new THREE.Vector3(-4, -3, 4.8), "#34d399");

            /* ── data spheres ── */
            for (const d of normalized) {
                const geo = new THREE.IcosahedronGeometry(Math.min(d.radius, 0.5), 1);
                const mat = new THREE.MeshPhysicalMaterial({
                    color: d.color.hex,
                    emissive: d.color.hex,
                    emissiveIntensity: 0.5,
                    roughness: 0.2,
                    metalness: 0.3,
                    transparent: true,
                    opacity: 0.85,
                    transmission: 0.15,
                });
                const mesh = new THREE.Mesh(geo, mat);
                mesh.position.set(d.x, d.y, d.z);
                mesh.userData = {
                    tooltipLabel: d.name,
                    tooltipRows: [
                        { key: "Score", value: (d.item.avg_score ?? 0).toFixed(2) },
                        { key: "Latency", value: `${Math.round(d.item.avg_latency_ms ?? 0)}ms` },
                        { key: "Cost", value: `$${Number(d.item.avg_cost_usd ?? 0).toFixed(4)}` },
                        { key: "Runs", value: String(d.item.n) },
                    ],
                };
                scene.add(mesh);
                api.hoverTargets.push(mesh);
                disposables.add(geo);
                disposables.add(mat);

                // glow
                const glowGeo = new THREE.IcosahedronGeometry(Math.min(d.radius, 0.5) * 1.6, 1);
                const glowMat = new THREE.MeshBasicMaterial({
                    color: d.color.hex, transparent: true, opacity: 0.08, side: THREE.BackSide,
                });
                mesh.add(new THREE.Mesh(glowGeo, glowMat));
                disposables.add(glowGeo);
                disposables.add(glowMat);

                // drop line
                const floorY = -3;
                const lineGeo = new THREE.BufferGeometry().setFromPoints([
                    new THREE.Vector3(d.x, d.y, d.z),
                    new THREE.Vector3(d.x, floorY, d.z),
                ]);
                const lineMat = new THREE.LineDashedMaterial({
                    color: d.color.hex, transparent: true, opacity: 0.2, dashSize: 0.15, gapSize: 0.1,
                });
                const line = new THREE.Line(lineGeo, lineMat);
                line.computeLineDistances();
                scene.add(line);
                disposables.add(lineGeo);
                disposables.add(lineMat);
            }

            /* ── pulse ── */
            let t = 0;
            api.onFrame.add((dt) => {
                t += dt;
                for (const target of api.hoverTargets) {
                    if (target instanceof THREE.Mesh) {
                        const s = 1 + Math.sin(t * 1.5 + target.position.x) * 0.03;
                        target.scale.setScalar(s);
                    }
                }
            });
        },
        [normalized],
    );

    return (
        <Scene3D
            onInit={onInit}
            cameraDistance={12}
            cameraY={5}
            autoRotate={0.2}
            containerRef={containerRef}
            cameraRef={cameraRef}
            targetsRef={targetsRef}
        >
            <LegendOverlay
                items={legendItems}
                title="Models"
                axes={{ x: "Score", y: "Latency (log)", z: "Cost ($)" }}
            />
            <TooltipOverlay data={tooltip} />
        </Scene3D>
    );
}
