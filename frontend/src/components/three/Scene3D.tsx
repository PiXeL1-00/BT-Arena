"use client";

import { useEffect, useRef, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three-stdlib";
import { EffectComposer, RenderPass, UnrealBloomPass } from "three-stdlib";

/* ───────────────────────── types ───────────────────────── */
export interface SceneApi {
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    renderer: THREE.WebGLRenderer;
    /** Add objects that should be raycasted for hover */
    hoverTargets: THREE.Object3D[];
    /** call per-frame, e.g. for custom animations */
    onFrame: Set<(dt: number) => void>;
    /** dispose helper */
    disposables: Set<{ dispose: () => void }>;
}

interface Scene3DProps {
    /** called once after the scene is ready — populate it here */
    onInit: (api: SceneApi) => void;
    className?: string;
    /** auto-rotate speed, 0 to disable */
    autoRotate?: number;
    /** camera distance */
    cameraDistance?: number;
    /** camera Y position */
    cameraY?: number;
    /** HTML overlay children (legends, tooltips) rendered on top of the canvas */
    children?: React.ReactNode;
    /** Ref to expose the camera for raycasting */
    cameraRef?: React.RefObject<THREE.PerspectiveCamera | null>;
    /** Ref to expose hover targets for raycasting */
    targetsRef?: React.RefObject<THREE.Object3D[]>;
    /** Ref to expose the container div */
    containerRef?: React.RefObject<HTMLDivElement | null>;
}

/* ───────────────────── starfield ───────────────────── */
function createStarfield(count: number): THREE.Points {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    for (let i = 0; i < count; i++) {
        const r = 40 + Math.random() * 60;
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
        positions[i * 3 + 2] = r * Math.cos(phi);
        sizes[i] = 0.5 + Math.random() * 1.5;
    }
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("size", new THREE.BufferAttribute(sizes, 1));
    const mat = new THREE.PointsMaterial({
        color: 0xffffff,
        size: 0.12,
        transparent: true,
        opacity: 0.6,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        sizeAttenuation: true,
    });
    return new THREE.Points(geo, mat);
}

/* ───────────────────── grid floor ───────────────────── */
function createGridFloor(): THREE.Group {
    const group = new THREE.Group();
    const grid = new THREE.GridHelper(20, 40, 0x1a2a3a, 0x0d1520);
    grid.position.y = -0.01;
    (grid.material as THREE.Material).transparent = true;
    (grid.material as THREE.Material).opacity = 0.35;
    group.add(grid);
    return group;
}

/* ══════════════════════ Component ══════════════════════ */
export default function Scene3D({
    onInit,
    className = "",
    autoRotate = 0.15,
    cameraDistance = 10,
    cameraY = 4,
    children,
    cameraRef: externalCameraRef,
    targetsRef: externalTargetsRef,
    containerRef: externalContainerRef,
}: Scene3DProps) {
    const divRef = useRef<HTMLDivElement>(null);
    const cleanupRef = useRef<(() => void) | null>(null);

    const init = useCallback(() => {
        const el = divRef.current;
        if (!el) return;

        /* ── sizes ── */
        const w = el.clientWidth || 600;
        const h = el.clientHeight || 400;

        /* ── renderer ── */
        const renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
            powerPreference: "high-performance",
        });
        renderer.setSize(w, h);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.1;
        renderer.outputColorSpace = THREE.SRGBColorSpace;

        // Clear existing canvases only
        const existingCanvas = el.querySelector("canvas");
        if (existingCanvas) existingCanvas.remove();
        el.prepend(renderer.domElement);

        /* ── scene ── */
        const scene = new THREE.Scene();
        scene.fog = new THREE.FogExp2(0x070b14, 0.025);

        /* ── camera ── */
        const camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 200);
        camera.position.set(cameraDistance * 0.7, cameraY, cameraDistance * 0.7);
        camera.lookAt(0, 0, 0);

        // Expose camera ref
        if (externalCameraRef) {
            (externalCameraRef as React.MutableRefObject<THREE.PerspectiveCamera | null>).current = camera;
        }

        /* ── orbit ── */
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.06;
        controls.autoRotate = autoRotate > 0;
        controls.autoRotateSpeed = autoRotate;
        controls.maxDistance = 30;
        controls.minDistance = 3;
        controls.maxPolarAngle = Math.PI * 0.85;

        /* ── lighting ── */
        const ambient = new THREE.HemisphereLight(0x4488cc, 0x220a00, 0.5);
        scene.add(ambient);
        const sun = new THREE.DirectionalLight(0xeef4ff, 1.0);
        sun.position.set(8, 12, 6);
        scene.add(sun);
        const fill = new THREE.PointLight(0xffaa55, 0.3, 40);
        fill.position.set(-6, 3, -8);
        scene.add(fill);

        /* ── env objects ── */
        const stars = createStarfield(2000);
        scene.add(stars);
        const gridFloor = createGridFloor();
        scene.add(gridFloor);

        /* ── bloom ── */
        const composer = new EffectComposer(renderer);
        composer.addPass(new RenderPass(scene, camera));
        const bloom = new UnrealBloomPass(
            new THREE.Vector2(w, h),
            1.0,  // strength
            0.5,  // radius
            0.35, // threshold
        );
        composer.addPass(bloom);

        /* ── API ── */
        const hoverTargets: THREE.Object3D[] = [];
        const onFrameCallbacks = new Set<(dt: number) => void>();
        const disposables = new Set<{ dispose: () => void }>();

        // Expose targets ref
        if (externalTargetsRef) {
            (externalTargetsRef as React.MutableRefObject<THREE.Object3D[]>).current = hoverTargets;
        }

        const api: SceneApi = {
            scene, camera, renderer,
            hoverTargets,
            onFrame: onFrameCallbacks,
            disposables,
        };

        // call user init
        onInit(api);

        /* ── animate ── */
        const clock = new THREE.Clock();
        let raf = 0;
        const animate = () => {
            raf = requestAnimationFrame(animate);
            const dt = clock.getDelta();
            controls.update();
            stars.rotation.y += 0.00008;
            onFrameCallbacks.forEach((fn) => fn(dt));
            composer.render();
        };
        animate();

        /* ── resize ── */
        const onResize = () => {
            if (!divRef.current) return;
            const rw = divRef.current.clientWidth;
            const rh = divRef.current.clientHeight;
            camera.aspect = rw / rh;
            camera.updateProjectionMatrix();
            renderer.setSize(rw, rh);
            composer.setSize(rw, rh);
            bloom.resolution.set(rw, rh);
        };
        window.addEventListener("resize", onResize);

        /* ── cleanup ── */
        cleanupRef.current = () => {
            window.removeEventListener("resize", onResize);
            cancelAnimationFrame(raf);
            controls.dispose();
            disposables.forEach((d) => d.dispose());
            renderer.dispose();
            composer.dispose();
            scene.traverse((obj) => {
                if (obj instanceof THREE.Mesh) {
                    obj.geometry?.dispose();
                    if (Array.isArray(obj.material)) {
                        obj.material.forEach((m) => m.dispose());
                    } else {
                        obj.material?.dispose();
                    }
                }
            });
        };
    }, [onInit, autoRotate, cameraDistance, cameraY, externalCameraRef, externalTargetsRef]);

    useEffect(() => {
        // Sync external containerRef with internal divRef
        if (externalContainerRef && divRef.current) {
            (externalContainerRef as React.MutableRefObject<HTMLDivElement | null>).current = divRef.current;
        }
        init();
        return () => {
            cleanupRef.current?.();
        };
    }, [init, externalContainerRef]);

    return (
        <div
            ref={divRef}
            className={`relative w-full h-full min-h-[320px] ${className}`}
            style={{ touchAction: "none" }}
        >
            {children}
        </div>
    );
}

