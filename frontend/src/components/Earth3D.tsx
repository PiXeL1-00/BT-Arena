"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

const Earth3D = () => {
    const containerRef = useRef<HTMLDivElement>(null);
    const rendererRef = useRef<THREE.WebGLRenderer | null>(null);

    useEffect(() => {
        if (!containerRef.current) return;

        // Scene setup
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 1000);
        camera.position.z = 9.8;

        // Renderer
        const renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
            powerPreference: "high-performance"
        });
        const width = containerRef.current.clientWidth || 800;
        const height = containerRef.current.clientHeight || 800;
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        rendererRef.current = renderer;

        camera.aspect = width / height;
        camera.updateProjectionMatrix();

        containerRef.current.innerHTML = '';
        containerRef.current.appendChild(renderer.domElement);

        // Ambient Lighting & Soft Accent Lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 1.5);
        scene.add(ambientLight);

        const pointLight1 = new THREE.PointLight(0x412ad1, 2.5, 25);
        pointLight1.position.set(7, 7, 7);
        scene.add(pointLight1);

        const pointLight2 = new THREE.PointLight(0xb50bbb, 2, 25);
        pointLight2.position.set(-7, -5, -5);
        scene.add(pointLight2);

        // =========================================================================
        // Non-spherical, organic cybernetic mesh with protruding nodes & dense edges
        // =========================================================================
        const numVertices = 200;
        const baseRadius = 3.1;

        // Structured vertex node data
        interface NodeData {
            direction: THREE.Vector3;
            baseDist: number;
            currentDist: number;
            isProtruding: boolean;
            protrusionFactor: number;
            phase: number;
            freq: number;
        }

        const nodes: NodeData[] = [];
        const basePositions: THREE.Vector3[] = [];

        // Fibonacci sphere / golden ratio distribution with noise-based non-spherical deformation
        const phi = (1 + Math.sqrt(5)) / 2;
        for (let i = 0; i < numVertices; i++) {
            const theta = 2 * Math.PI * i / phi;
            const y = 1 - (i / (numVertices - 1)) * 2;
            const radiusAtY = Math.sqrt(1 - y * y);
            const x = Math.cos(theta) * radiusAtY;
            const z = Math.sin(theta) * radiusAtY;

            const dir = new THREE.Vector3(x, y, z).normalize();

            // Non-spherical organic distortion (ellipsoidal + multi-frequency geometric distortion)
            const distortion = 1.0 + 0.35 * Math.sin(dir.x * 3.5 + dir.y * 2.2) * Math.cos(dir.z * 2.8);
            
            // 25% of nodes stick out of the main sphere shape
            const isProtruding = i % 4 === 0 || (i * 7) % numVertices < 15;
            const protrusionFactor = isProtruding ? 1.45 + (i % 5) * 0.12 : 1.0;
            const dist = baseRadius * distortion * (isProtruding ? protrusionFactor : 0.88 + (i % 3) * 0.08);

            nodes.push({
                direction: dir,
                baseDist: dist,
                currentDist: dist,
                isProtruding,
                protrusionFactor,
                phase: Math.random() * Math.PI * 2,
                freq: 0.6 + Math.random() * 0.8,
            });

            basePositions.push(dir.clone().multiplyScalar(dist));
        }

        // =========================================================================
        // Dense Edge Graph ("way more quantity of edges in same number of vertices")
        // =========================================================================
        // Connect each vertex to its K nearest neighbors (K = 12)
        const K_NEIGHBORS = 12;
        const edgePairs: [number, number][] = [];
        const edgeSet = new Set<string>();

        for (let i = 0; i < numVertices; i++) {
            // Find distances to all other nodes
            const dists: { index: number; dist: number }[] = [];
            for (let j = 0; j < numVertices; j++) {
                if (i === j) continue;
                const d = basePositions[i].distanceTo(basePositions[j]);
                dists.push({ index: j, dist: d });
            }
            dists.sort((a, b) => a.dist - b.dist);

            // Connect to K nearest
            for (let k = 0; k < Math.min(K_NEIGHBORS, dists.length); k++) {
                const j = dists[k].index;
                const key = i < j ? `${i}_${j}` : `${j}_${i}`;
                if (!edgeSet.has(key)) {
                    edgeSet.add(key);
                    edgePairs.push([i, j]);
                }
            }
        }

        // Create buffer geometry for thin edge lines
        const edgePositions = new Float32Array(edgePairs.length * 2 * 3);
        const linesGeometry = new THREE.BufferGeometry();
        linesGeometry.setAttribute('position', new THREE.BufferAttribute(edgePositions, 3));

        const linesMaterial = new THREE.LineBasicMaterial({
            color: 0x412ad1,
            transparent: true,
            opacity: 0.26,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
        });

        const linesMesh = new THREE.LineSegments(linesGeometry, linesMaterial);
        scene.add(linesMesh);

        // =========================================================================
        // Node Points (Core & Sticking Out Nodes)
        // =========================================================================
        const coreNodePositions = new Float32Array(numVertices * 3);
        const coreNodeGeometry = new THREE.BufferGeometry();
        coreNodeGeometry.setAttribute('position', new THREE.BufferAttribute(coreNodePositions, 3));

        const coreNodeMaterial = new THREE.PointsMaterial({
            color: 0x412ad1,
            size: 0.08,
            transparent: true,
            opacity: 0.7,
            sizeAttenuation: true,
            blending: THREE.AdditiveBlending,
        });
        const coreNodesMesh = new THREE.Points(coreNodeGeometry, coreNodeMaterial);
        scene.add(coreNodesMesh);

        // Highlight mesh specifically for protruding nodes sticking out
        const protrudeIndices = nodes.map((n, idx) => n.isProtruding ? idx : -1).filter(idx => idx !== -1);
        const protrudePositions = new Float32Array(protrudeIndices.length * 3);
        const protrudeGeometry = new THREE.BufferGeometry();
        protrudeGeometry.setAttribute('position', new THREE.BufferAttribute(protrudePositions, 3));

        const protrudeMaterial = new THREE.PointsMaterial({
            color: 0xb50bbb,
            size: 0.16,
            transparent: true,
            opacity: 0.95,
            sizeAttenuation: true,
            blending: THREE.AdditiveBlending,
        });
        const protrudeNodesMesh = new THREE.Points(protrudeGeometry, protrudeMaterial);
        scene.add(protrudeNodesMesh);

        // =========================================================================
        // Inner Core Lattice (Concentric Wireframe for multi-layer depth)
        // =========================================================================
        const innerGeometry = new THREE.IcosahedronGeometry(baseRadius * 0.55, 2);
        const innerMaterial = new THREE.MeshStandardMaterial({
            color: 0x412ad1,
            emissive: 0x412ad1,
            emissiveIntensity: 0.25,
            wireframe: true,
            transparent: true,
            opacity: 0.18,
            roughness: 0.3,
        });
        const innerMesh = new THREE.Mesh(innerGeometry, innerMaterial);
        scene.add(innerMesh);

        // =========================================================================
        // Animation Loop - Dynamic Mesh Wave & Protrusion Motion
        // =========================================================================
        let animationId: number;
        const clock = new THREE.Clock();

        const currentPosArr = new Array(numVertices).fill(0).map(() => new THREE.Vector3());

        const animate = () => {
            animationId = requestAnimationFrame(animate);
            const time = clock.getElapsedTime();

            // Update vertex distances and positions dynamically
            for (let i = 0; i < numVertices; i++) {
                const node = nodes[i];
                
                // Pulsating radial wave motion (protruding nodes extend further dynamically)
                const wave1 = Math.sin(time * node.freq + node.phase);
                const wave2 = Math.cos(time * 0.7 + node.direction.x * 2.5 + node.direction.y * 1.8);
                const pulse = wave1 * 0.18 + wave2 * 0.14;
                
                if (node.isProtruding) {
                    // Extra dynamic protrusion sticking out
                    const extrudeWave = Math.sin(time * 1.1 + node.phase) * 0.45;
                    node.currentDist = node.baseDist + extrudeWave;
                } else {
                    node.currentDist = node.baseDist + pulse;
                }

                currentPosArr[i].copy(node.direction).multiplyScalar(node.currentDist);

                // Update core node positions array
                coreNodePositions[i * 3] = currentPosArr[i].x;
                coreNodePositions[i * 3 + 1] = currentPosArr[i].y;
                coreNodePositions[i * 3 + 2] = currentPosArr[i].z;
            }
            coreNodeGeometry.attributes.position.needsUpdate = true;

            // Update protruding nodes position array
            for (let p = 0; p < protrudeIndices.length; p++) {
                const idx = protrudeIndices[p];
                protrudePositions[p * 3] = currentPosArr[idx].x;
                protrudePositions[p * 3 + 1] = currentPosArr[idx].y;
                protrudePositions[p * 3 + 2] = currentPosArr[idx].z;
            }
            protrudeGeometry.attributes.position.needsUpdate = true;

            // Update dense thin edge line segment positions
            for (let e = 0; e < edgePairs.length; e++) {
                const [i, j] = edgePairs[e];
                const p1 = currentPosArr[i];
                const p2 = currentPosArr[j];

                edgePositions[e * 6] = p1.x;
                edgePositions[e * 6 + 1] = p1.y;
                edgePositions[e * 6 + 2] = p1.z;

                edgePositions[e * 6 + 3] = p2.x;
                edgePositions[e * 6 + 4] = p2.y;
                edgePositions[e * 6 + 5] = p2.z;
            }
            linesGeometry.attributes.position.needsUpdate = true;

            // Ambient group rotations
            const rotY = time * 0.035;
            const rotX = Math.sin(time * 0.02) * 0.07;

            linesMesh.rotation.y = rotY;
            linesMesh.rotation.x = rotX;

            coreNodesMesh.rotation.y = rotY;
            coreNodesMesh.rotation.x = rotX;

            protrudeNodesMesh.rotation.y = rotY;
            protrudeNodesMesh.rotation.x = rotX;

            innerMesh.rotation.y = -time * 0.025;
            innerMesh.rotation.z = Math.cos(time * 0.02) * 0.08;

            renderer.render(scene, camera);
        };

        animate();

        const handleResize = () => {
            if (!containerRef.current) return;
            const width = containerRef.current.clientWidth;
            const height = containerRef.current.clientHeight;
            camera.aspect = width / height;
            camera.updateProjectionMatrix();
            renderer.setSize(width, height);
        };

        handleResize();
        window.addEventListener("resize", handleResize);

        return () => {
            window.removeEventListener("resize", handleResize);
            cancelAnimationFrame(animationId);
            renderer.dispose();
            linesGeometry.dispose();
            linesMaterial.dispose();
            coreNodeGeometry.dispose();
            coreNodeMaterial.dispose();
            protrudeGeometry.dispose();
            protrudeMaterial.dispose();
            innerGeometry.dispose();
            innerMaterial.dispose();
        };
    }, []);

    return (
        <div
            ref={containerRef}
            className="absolute inset-0 w-full h-full"
        />
    );
};

export default Earth3D;
