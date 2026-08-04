"use client";

import { useCallback, useMemo, useRef } from "react";
import * as THREE from "three";
import Scene3D, { type SceneApi } from "./Scene3D";
import { LegendOverlay, TooltipOverlay, useHoverRaycast } from "./Overlays";
import type { ModelTrendSeries } from "@/lib/galileoTypes";

/* ───── palette ───── */
const RIBBON_COLORS: { hex: number; css: string }[] = [
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
    series: ModelTrendSeries[];
    modelNames: Map<string, string>;
}

export default function TrendCurrents3D({ series, modelNames }: Props) {
    const containerRef = useRef<HTMLDivElement>(null);
    const cameraRef = useRef<THREE.PerspectiveCamera>(null);
    const targetsRef = useRef<THREE.Object3D[]>([]);

    const tooltip = useHoverRaycast(containerRef, cameraRef, targetsRef);

    /* ── legend ── */
    const legendItems = useMemo(
        () =>
            series.map((s, i) => ({
                label: modelNames.get(s.llm_id) ?? s.llm_id.slice(0, 12),
                color: RIBBON_COLORS[i % RIBBON_COLORS.length].css,
                value: s.buckets.length > 0 ? `${(s.buckets[s.buckets.length - 1].score_avg ?? 0).toFixed(1)}` : "—",
            })),
        [series, modelNames],
    );

    const onInit = useCallback(
        (api: SceneApi) => {
            const { scene, disposables } = api;

            const SCALE_X = 8;
            const SCALE_Y = 4;
            const seriesCount = series.length;
            const zStep = 1.6;
            const zBase = -((seriesCount - 1) * zStep) / 2;

            /* ── collect all dates for axis ── */
            const allDates = new Set<string>();
            for (const s of series) {
                for (const pt of s.buckets) allDates.add(pt.bucket);
            }
            const sortedDates = Array.from(allDates).sort();
            const dateCount = sortedDates.length;
            if (dateCount === 0) return;

            /* ── time axis marks on floor ── */
            const labelInterval = Math.max(1, Math.floor(dateCount / 6));
            for (let i = 0; i < dateCount; i++) {
                if (i % labelInterval !== 0 && i !== dateCount - 1) continue;
                const x = (i / Math.max(dateCount - 1, 1)) * SCALE_X - SCALE_X / 2;
                // tick mark
                const tickGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.3, 4);
                const tickMat = new THREE.MeshBasicMaterial({ color: 0x3a5a7a, transparent: true, opacity: 0.5 });
                const tick = new THREE.Mesh(tickGeo, tickMat);
                tick.position.set(x, -0.15, -zBase - 1.5);
                scene.add(tick);
                disposables.add(tickGeo);
                disposables.add(tickMat);
            }

            for (let si = 0; si < seriesCount; si++) {
                const s = series[si];
                const color = RIBBON_COLORS[si % RIBBON_COLORS.length];
                const mName = modelNames.get(s.llm_id) ?? s.llm_id.slice(0, 12);
                const z = zBase + si * zStep;

                if (s.buckets.length < 2) continue;

                // build curve
                const curvePoints: THREE.Vector3[] = [];
                for (let pi = 0; pi < s.buckets.length; pi++) {
                    const pt = s.buckets[pi];
                    const dateIdx = sortedDates.indexOf(pt.bucket);
                    const t = dateIdx / Math.max(dateCount - 1, 1);
                    const x = t * SCALE_X - SCALE_X / 2;
                    const y = ((pt.score_avg ?? 0) / 100) * SCALE_Y;
                    curvePoints.push(new THREE.Vector3(x, Math.max(y, 0.02), z));
                }

                // tube ribbon
                const curve = new THREE.CatmullRomCurve3(curvePoints, false, "catmullrom", 0.3);
                const tubeGeo = new THREE.TubeGeometry(curve, Math.max(curvePoints.length * 8, 32), 0.06, 8, false);

                // vertex colors — recency gradient
                const count = tubeGeo.getAttribute("position").count;
                const colors = new Float32Array(count * 3);
                const cBase = new THREE.Color(color.hex);
                for (let ci = 0; ci < count; ci++) {
                    const pos = new THREE.Vector3().fromBufferAttribute(tubeGeo.getAttribute("position") as THREE.BufferAttribute, ci);
                    const tNorm = (pos.x + SCALE_X / 2) / SCALE_X;
                    const alpha = 0.3 + tNorm * 0.7;
                    colors[ci * 3] = cBase.r * alpha;
                    colors[ci * 3 + 1] = cBase.g * alpha;
                    colors[ci * 3 + 2] = cBase.b * alpha;
                }
                tubeGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));

                const tubeMat = new THREE.MeshPhysicalMaterial({
                    vertexColors: true,
                    emissive: color.hex,
                    emissiveIntensity: 0.25,
                    roughness: 0.3,
                    metalness: 0.4,
                    transparent: true,
                    opacity: 0.85,
                });
                const tube = new THREE.Mesh(tubeGeo, tubeMat);
                scene.add(tube);
                disposables.add(tubeGeo);
                disposables.add(tubeMat);

                // data point markers (hoverable)
                for (let pi = 0; pi < s.buckets.length; pi++) {
                    const pt = s.buckets[pi];
                    const dateIdx = sortedDates.indexOf(pt.bucket);
                    const t = dateIdx / Math.max(dateCount - 1, 1);
                    const x = t * SCALE_X - SCALE_X / 2;
                    const y = ((pt.score_avg ?? 0) / 100) * SCALE_Y;

                    const dotGeo = new THREE.SphereGeometry(0.09, 10, 10);
                    const dotMat = new THREE.MeshBasicMaterial({
                        color: color.hex, transparent: true, opacity: 0.9,
                    });
                    const dot = new THREE.Mesh(dotGeo, dotMat);
                    dot.position.set(x, Math.max(y, 0.02), z);
                    dot.userData = {
                        tooltipLabel: mName,
                        tooltipRows: [
                            { key: "Date", value: pt.bucket },
                            { key: "Score", value: (pt.score_avg ?? 0).toFixed(2) },
                        ],
                    };
                    scene.add(dot);
                    api.hoverTargets.push(dot);
                    disposables.add(dotGeo);
                    disposables.add(dotMat);
                }

                // glow tube
                const glowGeo = new THREE.TubeGeometry(curve, Math.max(curvePoints.length * 4, 16), 0.14, 6, false);
                const glowMat = new THREE.MeshBasicMaterial({
                    color: color.hex, transparent: true, opacity: 0.06, side: THREE.BackSide,
                });
                scene.add(new THREE.Mesh(glowGeo, glowMat));
                disposables.add(glowGeo);
                disposables.add(glowMat);
            }

            // gentle shimmer
            let t = 0;
            api.onFrame.add((dt) => {
                t += dt;
                scene.traverse((obj) => {
                    if (obj instanceof THREE.Mesh && obj.material instanceof THREE.MeshPhysicalMaterial) {
                        obj.material.emissiveIntensity = 0.2 + Math.sin(t * 1.5) * 0.08;
                    }
                });
            });
        },
        [series, modelNames],
    );

    return (
        <Scene3D
            onInit={onInit}
            cameraDistance={11}
            cameraY={5}
            autoRotate={0.12}
            containerRef={containerRef}
            cameraRef={cameraRef}
            targetsRef={targetsRef}
        >
            <LegendOverlay
                items={legendItems}
                title="Models (latest score)"
                axes={{ x: "Time →", y: "Score ↑" }}
            />
            <TooltipOverlay data={tooltip} />
        </Scene3D>
    );
}
