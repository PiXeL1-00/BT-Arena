"use client";

import { useCallback, useMemo, useRef } from "react";
import * as THREE from "three";
import Scene3D, { type SceneApi } from "./Scene3D";
import { LegendOverlay, DimensionLegend, TooltipOverlay, useHoverRaycast } from "./Overlays";
import type { ScoreBreakdownItem } from "@/lib/galileoTypes";

/* ───── dimension config ───── */
const DIMENSIONS = [
    { key: "correctness" as const, label: "Correctness", hex: 0x22d3ee, css: "#22d3ee" },
    { key: "grounding" as const, label: "Grounding", hex: 0x34d399, css: "#34d399" },
    { key: "calibration" as const, label: "Calibration", hex: 0xa78bfa, css: "#a78bfa" },
    { key: "falsifiable" as const, label: "Falsifiable", hex: 0xf59e0b, css: "#f59e0b" },
];

const PENALTY_DIMS = [
    { key: "deference_penalty" as const, label: "Deference ↓", hex: 0xf43f5e, css: "#f43f5e" },
    { key: "refusal_penalty" as const, label: "Refusal ↓", hex: 0xfb7185, css: "#fb7185" },
];

interface Props {
    items: ScoreBreakdownItem[];
    modelNames: Map<string, string>;
}

export default function ScorePeaks3D({ items, modelNames }: Props) {
    const containerRef = useRef<HTMLDivElement>(null);
    const cameraRef = useRef<THREE.PerspectiveCamera>(null);
    const targetsRef = useRef<THREE.Object3D[]>([]);

    const tooltip = useHoverRaycast(containerRef, cameraRef, targetsRef);

    const sortedItems = useMemo(
        () =>
            [...items].sort((a, b) => {
                const aScore = a.correctness + a.grounding + a.calibration + a.falsifiable;
                const bScore = b.correctness + b.grounding + b.calibration + b.falsifiable;
                return bScore - aScore;
            }),
        [items],
    );

    /* ── model legend ── */
    const modelLegend = useMemo(
        () =>
            sortedItems.map((item, i) => ({
                label: modelNames.get(item.llm_id) ?? item.llm_id.slice(0, 12),
                color: "#67e8f9",
                value: `${(item.correctness + item.grounding + item.calibration + item.falsifiable).toFixed(0)}`,
            })),
        [sortedItems, modelNames],
    );

    const dimLegend = useMemo(
        () => [
            ...DIMENSIONS.map((d) => ({ label: d.label, color: d.css })),
            ...PENALTY_DIMS.map((d) => ({ label: d.label, color: d.css })),
        ],
        [],
    );

    const onInit = useCallback(
        (api: SceneApi) => {
            const { scene, disposables } = api;

            const modelCount = sortedItems.length;
            const dimCount = DIMENSIONS.length;
            const spacing = 1.6;
            const barWidth = 0.28;
            const maxHeight = 3.5;
            const floorY = 0;

            const totalWidth = modelCount * spacing;
            const offsetX = -totalWidth / 2 + spacing / 2;
            const offsetZ = -dimCount * spacing * 0.3;

            for (let mi = 0; mi < modelCount; mi++) {
                const item = sortedItems[mi];
                const mName = modelNames.get(item.llm_id) ?? item.llm_id.slice(0, 12);

                for (let di = 0; di < DIMENSIONS.length; di++) {
                    const dim = DIMENSIONS[di];
                    const val = item[dim.key];
                    const h = val * maxHeight;
                    if (h < 0.01) continue;

                    const geo = new THREE.BoxGeometry(barWidth, h, barWidth);
                    const mat = new THREE.MeshPhysicalMaterial({
                        color: dim.hex,
                        emissive: dim.hex,
                        emissiveIntensity: 0.25,
                        roughness: 0.15,
                        metalness: 0.35,
                        transparent: true,
                        opacity: 0.8,
                        transmission: 0.2,
                    });
                    const mesh = new THREE.Mesh(geo, mat);
                    mesh.position.set(
                        offsetX + mi * spacing + di * barWidth * 1.3 - (dimCount * barWidth * 1.3) / 2,
                        floorY + h / 2,
                        offsetZ + di * spacing * 0.5,
                    );
                    mesh.userData = {
                        tooltipLabel: `${mName} — ${dim.label}`,
                        tooltipRows: [
                            { key: dim.label, value: val.toFixed(2) },
                            { key: "Runs", value: String(item.n) },
                        ],
                    };
                    scene.add(mesh);
                    api.hoverTargets.push(mesh);
                    disposables.add(geo);
                    disposables.add(mat);

                    // cap
                    const capGeo = new THREE.PlaneGeometry(barWidth * 1.1, barWidth * 1.1);
                    const capMat = new THREE.MeshBasicMaterial({
                        color: dim.hex, transparent: true, opacity: 0.6, side: THREE.DoubleSide,
                    });
                    const cap = new THREE.Mesh(capGeo, capMat);
                    cap.rotation.x = -Math.PI / 2;
                    cap.position.set(mesh.position.x, floorY + h + 0.01, mesh.position.z);
                    scene.add(cap);
                    disposables.add(capGeo);
                    disposables.add(capMat);
                }

                // penalties
                for (let pi = 0; pi < PENALTY_DIMS.length; pi++) {
                    const pen = PENALTY_DIMS[pi];
                    const val = item[pen.key];
                    if (val < 0.001) continue;
                    const h = val * maxHeight * 0.5;

                    const geo = new THREE.BoxGeometry(barWidth * 0.7, h, barWidth * 0.7);
                    const mat = new THREE.MeshPhysicalMaterial({
                        color: pen.hex, emissive: pen.hex, emissiveIntensity: 0.3,
                        roughness: 0.3, metalness: 0.2, transparent: true, opacity: 0.7,
                    });
                    const mesh = new THREE.Mesh(geo, mat);
                    mesh.position.set(
                        offsetX + mi * spacing + pi * barWidth * 1.3 - barWidth,
                        floorY - h / 2 - 0.05,
                        offsetZ + (DIMENSIONS.length + pi) * spacing * 0.4,
                    );
                    mesh.userData = {
                        tooltipLabel: `${mName} — ${pen.label}`,
                        tooltipRows: [{ key: "Penalty", value: val.toFixed(3) }],
                    };
                    scene.add(mesh);
                    api.hoverTargets.push(mesh);
                    disposables.add(geo);
                    disposables.add(mat);
                }
            }

            // shimmer
            let t = 0;
            api.onFrame.add((dt) => {
                t += dt;
                for (const target of api.hoverTargets) {
                    if (target instanceof THREE.Mesh && target.material instanceof THREE.MeshPhysicalMaterial) {
                        target.material.emissiveIntensity = 0.2 + Math.sin(t * 2 + target.position.x * 3) * 0.1;
                    }
                }
            });
        },
        [sortedItems, modelNames],
    );

    return (
        <Scene3D
            onInit={onInit}
            cameraDistance={10}
            cameraY={6}
            autoRotate={0.15}
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
