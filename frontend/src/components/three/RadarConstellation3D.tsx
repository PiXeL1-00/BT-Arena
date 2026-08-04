"use client";

import { useCallback, useMemo, useRef } from "react";
import * as THREE from "three";
import Scene3D, { type SceneApi } from "./Scene3D";
import { LegendOverlay, DimensionLegend, TooltipOverlay, useHoverRaycast } from "./Overlays";
import type { RadarEntry } from "@/lib/galileoTypes";

/* ───── distinct dimension colors ───── */
const DIMENSION_COLORS: Record<string, { hex: number; css: string }> = {
    correctness: { hex: 0x22d3ee, css: "#22d3ee" },  // cyan
    grounding: { hex: 0x34d399, css: "#34d399" },  // emerald
    calibration: { hex: 0xa78bfa, css: "#a78bfa" },  // violet
    falsifiable: { hex: 0xf59e0b, css: "#f59e0b" },  // amber
    deference_penalty: { hex: 0xf43f5e, css: "#f43f5e" },  // rose
    refusal_penalty: { hex: 0xfb7185, css: "#fb7185" },  // pink
};
const FALLBACK_DIM_COLOR = { hex: 0x818cf8, css: "#818cf8" };

/* ───── model colors (for polygons) ───── */
const MODEL_COLORS: { hex: number; css: string }[] = [
    { hex: 0x22d3ee, css: "#22d3ee" },
    { hex: 0xf59e0b, css: "#f59e0b" },
    { hex: 0x34d399, css: "#34d399" },
    { hex: 0xf43f5e, css: "#f43f5e" },
    { hex: 0xa78bfa, css: "#a78bfa" },
    { hex: 0xfb923c, css: "#fb923c" },
    { hex: 0x67e8f9, css: "#67e8f9" },
    { hex: 0x818cf8, css: "#818cf8" },
];

interface Props {
    entries: RadarEntry[];
    modelNames: Map<string, string>;
}

function dimColor(dim: string): { hex: number; css: string } {
    return DIMENSION_COLORS[dim] ?? FALLBACK_DIM_COLOR;
}

function prettyDim(dim: string): string {
    return dim
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function RadarConstellation3D({ entries, modelNames }: Props) {
    const containerRef = useRef<HTMLDivElement>(null);
    const cameraRef = useRef<THREE.PerspectiveCamera>(null);
    const targetsRef = useRef<THREE.Object3D[]>([]);

    const tooltip = useHoverRaycast(containerRef, cameraRef, targetsRef);

    /* ── group by model ── */
    const grouped = useMemo(() => {
        const map = new Map<string, { dim: string; val: number }[]>();
        for (const e of entries) {
            if (!map.has(e.llm_id)) map.set(e.llm_id, []);
            map.get(e.llm_id)!.push({ dim: e.dimension, val: e.avg_value ?? 0 });
        }
        return map;
    }, [entries]);

    const dimensions = useMemo(() => {
        const dims = new Set<string>();
        for (const e of entries) dims.add(e.dimension);
        return Array.from(dims);
    }, [entries]);

    /* ── model legend ── */
    const modelLegend = useMemo(() => {
        let idx = 0;
        const items: { label: string; color: string }[] = [];
        for (const [llmId] of Array.from(grouped)) {
            items.push({
                label: modelNames.get(llmId) ?? llmId.slice(0, 15),
                color: MODEL_COLORS[idx % MODEL_COLORS.length].css,
            });
            idx++;
        }
        return items;
    }, [grouped, modelNames]);

    /* ── dimension legend with DISTINCT colors ── */
    const dimLegend = useMemo(
        () =>
            dimensions.map((d) => ({
                label: prettyDim(d),
                color: dimColor(d).css,
            })),
        [dimensions],
    );

    const onInit = useCallback(
        (api: SceneApi) => {
            const { scene, disposables } = api;

            const axisCount = dimensions.length;
            if (axisCount === 0) return;
            const angleStep = (Math.PI * 2) / axisCount;
            const maxRadius = 3.5;

            /* ── concentric reference rings ── */
            const ringLevels = [0.25, 0.5, 0.75, 1.0];
            for (const level of ringLevels) {
                const r = level * maxRadius;
                const points: THREE.Vector3[] = [];
                for (let i = 0; i <= 64; i++) {
                    const a = (i / 64) * Math.PI * 2;
                    points.push(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r));
                }
                const geo = new THREE.BufferGeometry().setFromPoints(points);
                const mat = new THREE.LineBasicMaterial({
                    color: 0x1e3a5f,
                    transparent: true,
                    opacity: level === 1.0 ? 0.5 : 0.2 + level * 0.1,
                });
                scene.add(new THREE.Line(geo, mat));
                disposables.add(geo);
                disposables.add(mat);
            }

            /* ── color-coded axis spokes — one per dimension ── */
            for (let i = 0; i < axisCount; i++) {
                const dim = dimensions[i];
                const dc = dimColor(dim);
                const angle = i * angleStep - Math.PI / 2;
                const dx = Math.cos(angle);
                const dz = Math.sin(angle);

                // spoke line in dimension color
                const spokePoints = [
                    new THREE.Vector3(0, 0, 0),
                    new THREE.Vector3(dx * maxRadius, 0, dz * maxRadius),
                ];
                const spokeGeo = new THREE.BufferGeometry().setFromPoints(spokePoints);
                const spokeMat = new THREE.LineBasicMaterial({
                    color: dc.hex,
                    transparent: true,
                    opacity: 0.45,
                });
                scene.add(new THREE.Line(spokeGeo, spokeMat));
                disposables.add(spokeGeo);
                disposables.add(spokeMat);

                // colored endpoint sphere for the dimension
                const tipGeo = new THREE.IcosahedronGeometry(0.12, 1);
                const tipMat = new THREE.MeshPhysicalMaterial({
                    color: dc.hex,
                    emissive: dc.hex,
                    emissiveIntensity: 0.6,
                    roughness: 0.2,
                    metalness: 0.3,
                    transparent: true,
                    opacity: 0.9,
                });
                const tip = new THREE.Mesh(tipGeo, tipMat);
                tip.position.set(dx * maxRadius, 0, dz * maxRadius);
                tip.userData = {
                    tooltipLabel: prettyDim(dim),
                    tooltipRows: [{ key: "Axis", value: `${(i + 1)}/${axisCount}` }],
                };
                scene.add(tip);
                api.hoverTargets.push(tip);
                disposables.add(tipGeo);
                disposables.add(tipMat);

                // glow behind endpoint
                const glowGeo = new THREE.IcosahedronGeometry(0.22, 1);
                const glowMat = new THREE.MeshBasicMaterial({
                    color: dc.hex,
                    transparent: true,
                    opacity: 0.12,
                    side: THREE.BackSide,
                });
                tip.add(new THREE.Mesh(glowGeo, glowMat));
                disposables.add(glowGeo);
                disposables.add(glowMat);
            }

            /* ── model polygons — each model gets a distinctly colored shape ── */
            let modelIdx = 0;
            const yStep = 0.9;
            const totalModels = grouped.size;
            const yBase = -((totalModels - 1) * yStep) / 2;

            for (const [llmId, dimValues] of Array.from(grouped)) {
                const yOffset = yBase + modelIdx * yStep;
                const color = MODEL_COLORS[modelIdx % MODEL_COLORS.length];
                const mName = modelNames.get(llmId) ?? llmId.slice(0, 15);

                const shape = new THREE.Shape();
                const edgePoints: THREE.Vector3[] = [];

                for (let i = 0; i < axisCount; i++) {
                    const dim = dimensions[i];
                    const entry = dimValues.find((d: { dim: string; val: number }) => d.dim === dim);
                    const val = Math.max(entry?.val ?? 0, 0.02);
                    const r = val * maxRadius;
                    const angle = i * angleStep - Math.PI / 2;
                    const px = Math.cos(angle) * r;
                    const pz = Math.sin(angle) * r;

                    if (i === 0) shape.moveTo(px, pz);
                    else shape.lineTo(px, pz);
                    edgePoints.push(new THREE.Vector3(px, yOffset, pz));
                }
                shape.closePath();
                edgePoints.push(edgePoints[0].clone());

                // translucent fill
                const shapeGeo = new THREE.ShapeGeometry(shape);
                const shapeMat = new THREE.MeshPhysicalMaterial({
                    color: color.hex,
                    emissive: color.hex,
                    emissiveIntensity: 0.15,
                    transparent: true,
                    opacity: 0.22,
                    side: THREE.DoubleSide,
                    roughness: 0.4,
                    metalness: 0.3,
                });
                const shapeMesh = new THREE.Mesh(shapeGeo, shapeMat);
                shapeMesh.rotation.x = -Math.PI / 2;
                shapeMesh.position.y = yOffset;
                scene.add(shapeMesh);
                disposables.add(shapeGeo);
                disposables.add(shapeMat);

                // wire outline in model color
                const wireGeo = new THREE.BufferGeometry().setFromPoints(edgePoints);
                const wireMat = new THREE.LineBasicMaterial({
                    color: color.hex,
                    transparent: true,
                    opacity: 0.8,
                });
                scene.add(new THREE.Line(wireGeo, wireMat));
                disposables.add(wireGeo);
                disposables.add(wireMat);

                // vertex dots — hoverable, show the dimension value
                for (let i = 0; i < edgePoints.length - 1; i++) {
                    const dim = dimensions[i];
                    const dc = dimColor(dim);
                    const dimVal = dimValues.find((d: { dim: string; val: number }) => d.dim === dim)?.val ?? 0;

                    const dotGeo = new THREE.SphereGeometry(0.1, 12, 12);
                    const dotMat = new THREE.MeshPhysicalMaterial({
                        color: dc.hex,
                        emissive: dc.hex,
                        emissiveIntensity: 0.5,
                        roughness: 0.2,
                        metalness: 0.3,
                        transparent: true,
                        opacity: 0.9,
                    });
                    const dot = new THREE.Mesh(dotGeo, dotMat);
                    dot.position.copy(edgePoints[i]);
                    dot.userData = {
                        tooltipLabel: mName,
                        tooltipRows: [
                            { key: prettyDim(dim), value: dimVal.toFixed(3) },
                        ],
                    };
                    scene.add(dot);
                    api.hoverTargets.push(dot);
                    disposables.add(dotGeo);
                    disposables.add(dotMat);
                }

                modelIdx++;
            }

            // gentle breathing animation
            let t = 0;
            api.onFrame.add((dt) => {
                t += dt;
                scene.traverse((obj) => {
                    if (
                        obj instanceof THREE.Mesh &&
                        obj.material instanceof THREE.MeshPhysicalMaterial &&
                        obj.material.emissiveIntensity > 0.1
                    ) {
                        const base = obj.userData?.tooltipLabel ? 0.4 : 0.12;
                        obj.material.emissiveIntensity = base + Math.sin(t * 1.2 + obj.position.x) * 0.08;
                    }
                });
            });
        },
        [grouped, dimensions, modelNames],
    );

    return (
        <Scene3D
            onInit={onInit}
            cameraDistance={9}
            cameraY={4}
            autoRotate={0.25}
            containerRef={containerRef}
            cameraRef={cameraRef}
            targetsRef={targetsRef}
        >
            <LegendOverlay items={modelLegend} title="Models" />
            <DimensionLegend dimensions={dimLegend} title="Dimensions" />
            <TooltipOverlay data={tooltip} />
        </Scene3D>
    );
}
