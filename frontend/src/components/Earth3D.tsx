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
        camera.position.z = 9.5;

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

        // Ambient Lighting & Subtle Soft Lights
        const ambientLight = new THREE.AmbientLight(0x0f172a, 1.5);
        scene.add(ambientLight);

        const pointLight1 = new THREE.PointLight(0x06b6d4, 2, 20); // Soft cyan
        pointLight1.position.set(6, 6, 6);
        scene.add(pointLight1);

        const pointLight2 = new THREE.PointLight(0x6366f1, 1.5, 20); // Soft violet
        pointLight2.position.set(-6, -4, -4);
        scene.add(pointLight2);

        // Abstract 3D Wireframe / Data Mesh Structure
        const radius = 3.4;
        const detail = 3;

        // Outer Geodesic Wireframe Mesh
        const outerGeometry = new THREE.IcosahedronGeometry(radius, detail);
        const initialPositions = outerGeometry.attributes.position.clone();

        const outerMaterial = new THREE.MeshStandardMaterial({
            color: 0x0284c7,
            emissive: 0x0369a1,
            emissiveIntensity: 0.25,
            wireframe: true,
            transparent: true,
            opacity: 0.38,
            roughness: 0.2,
            metalness: 0.8,
        });

        const outerMesh = new THREE.Mesh(outerGeometry, outerMaterial);
        scene.add(outerMesh);

        // Data Nodes (Vertices Points)
        const nodesMaterial = new THREE.PointsMaterial({
            color: 0x38bdf8,
            size: 0.07,
            transparent: true,
            opacity: 0.75,
            sizeAttenuation: true,
        });

        const nodesMesh = new THREE.Points(outerGeometry, nodesMaterial);
        scene.add(nodesMesh);

        // Inner Core Lattice (Concentric Wireframe)
        const innerGeometry = new THREE.IcosahedronGeometry(radius * 0.65, 2);
        const innerMaterial = new THREE.MeshStandardMaterial({
            color: 0x6366f1,
            emissive: 0x4f46e5,
            emissiveIntensity: 0.2,
            wireframe: true,
            transparent: true,
            opacity: 0.25,
        });

        const innerMesh = new THREE.Mesh(innerGeometry, innerMaterial);
        scene.add(innerMesh);

        // Subtle Ambient Glow Sphere behind mesh
        const glowGeometry = new THREE.SphereGeometry(radius * 0.95, 32, 32);
        const glowMaterial = new THREE.MeshBasicMaterial({
            color: 0x0369a1,
            transparent: true,
            opacity: 0.05,
            side: THREE.BackSide,
        });
        const glowMesh = new THREE.Mesh(glowGeometry, glowMaterial);
        scene.add(glowMesh);

        // Animation Loop - Subtle, Slow Organic Motion
        let animationId: number;
        const clock = new THREE.Clock();

        const animate = () => {
            animationId = requestAnimationFrame(animate);
            const time = clock.getElapsedTime();

            // Organic Vertex Wave Deformation
            const pos = outerGeometry.attributes.position;
            const initPos = initialPositions;
            for (let i = 0; i < pos.count; i++) {
                const uX = initPos.getX(i);
                const uY = initPos.getY(i);
                const uZ = initPos.getZ(i);

                const len = Math.sqrt(uX * uX + uY * uY + uZ * uZ);
                const nx = uX / len;
                const ny = uY / len;
                const nz = uZ / len;

                // Subtle multi-harmonic wave
                const wave = Math.sin(time * 0.7 + uX * 0.8 + uY * 0.5) * Math.cos(time * 0.5 + uZ * 0.7) * 0.14;
                pos.setXYZ(i, uX + nx * wave, uY + ny * wave, uZ + nz * wave);
            }
            pos.needsUpdate = true;
            outerGeometry.computeVertexNormals();

            // Slow, ambient rotations
            outerMesh.rotation.y = time * 0.04;
            outerMesh.rotation.x = Math.sin(time * 0.02) * 0.08;

            nodesMesh.rotation.y = time * 0.04;
            nodesMesh.rotation.x = Math.sin(time * 0.02) * 0.08;

            innerMesh.rotation.y = -time * 0.03;
            innerMesh.rotation.z = Math.cos(time * 0.025) * 0.1;

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
            outerGeometry.dispose();
            outerMaterial.dispose();
            nodesMaterial.dispose();
            innerGeometry.dispose();
            innerMaterial.dispose();
            glowGeometry.dispose();
            glowMaterial.dispose();
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

