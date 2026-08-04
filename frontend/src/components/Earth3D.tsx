"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

const Earth3D = () => {
    const containerRef = useRef<HTMLDivElement>(null);
    const rendererRef = useRef<THREE.WebGLRenderer | null>(null);

    useEffect(() => {
        if (!containerRef.current) return;

        // Scene setup - adjusted camera distance
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 1000);
        camera.position.z = 10.12;

        // Renderer - full size
        const renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true
        });
        // Start with container size
        const width = containerRef.current.clientWidth || 800;
        const height = containerRef.current.clientHeight || 800;
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        rendererRef.current = renderer;

        // Update camera aspect
        camera.aspect = width / height;
        camera.updateProjectionMatrix();

        containerRef.current.innerHTML = '';
        containerRef.current.appendChild(renderer.domElement);

        // Lighting - exactly matching source
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
        scene.add(ambientLight);

        // const directionalLight = new THREE.DirectionalLight(0xffffff, 1.8);
        // directionalLight.position.set(5, 3, 5);
        // scene.add(directionalLight);

        // const pointLight1 = new THREE.PointLight(0xff8866, 0.4);
        // pointLight1.position.set(-8, -5, -8);
        // scene.add(pointLight1);

        // const pointLight2 = new THREE.PointLight(0xaaccff, 0.3);
        // pointLight2.position.set(8, 5, 8);
        // scene.add(pointLight2);

        // Mars sphere
        const textureLoader = new THREE.TextureLoader();
        const marsGeometry = new THREE.SphereGeometry(3.2, 64, 64);
        const marsMaterial = new THREE.MeshStandardMaterial({
            emissive: new THREE.Color(0x401008),
            emissiveIntensity: 0.15,
            roughness: 0.7,
            metalness: 0.1,
        });

        textureLoader.load(
            // "/mars-texture.webp",
            "/bt_mesh.png",
            (texture) => {
                texture.colorSpace = THREE.SRGBColorSpace;
                marsMaterial.map = texture;
                marsMaterial.needsUpdate = true;
            },
            undefined,
            (error) => {
                console.error("Error loading Mars texture:", error);
                marsMaterial.color = new THREE.Color(0xc1440e);
            }
        );

        const mars = new THREE.Mesh(marsGeometry, marsMaterial);
        // Mars axial tilt: 25.19 degrees
        mars.rotation.x = THREE.MathUtils.degToRad(25.19);
        scene.add(mars);

        // Phobos - grayish-taupe, elongated potato shape (like MRO image)
        const phobosGeometry = new THREE.DodecahedronGeometry(0.18, 1);
        const phobosPositions = phobosGeometry.attributes.position;
        for (let i = 0; i < phobosPositions.count; i++) {
            const x = phobosPositions.getX(i);
            const y = phobosPositions.getY(i);
            const z = phobosPositions.getZ(i);
            // Elongated potato with slight asymmetry
            phobosPositions.setX(i, x * 1.6);
            phobosPositions.setY(i, y * 0.75);
            phobosPositions.setZ(i, z * 0.85);
        }
        phobosGeometry.computeVertexNormals();
        const phobosMaterial = new THREE.MeshStandardMaterial({
            color: 0xa09890, // Grayish-taupe like MRO image
            roughness: 1.0,
            metalness: 0.0,
            flatShading: true,
        });
        const phobos = new THREE.Mesh(phobosGeometry, phobosMaterial);
        const phobosOrbit = new THREE.Group();
        phobos.position.set(4.5, 0, 0);
        phobosOrbit.rotation.x = THREE.MathUtils.degToRad(25.19);
        phobosOrbit.add(phobos);
        scene.add(phobosOrbit);

        // Deimos - yellowish-tan, rounder lumpy shape (like MRO image)
        const deimosGeometry = new THREE.DodecahedronGeometry(0.12, 1);
        const deimosPositions = deimosGeometry.attributes.position;
        for (let i = 0; i < deimosPositions.count; i++) {
            const x = deimosPositions.getX(i);
            const y = deimosPositions.getY(i);
            const z = deimosPositions.getZ(i);
            // Rounder but still lumpy
            deimosPositions.setX(i, x * 1.2);
            deimosPositions.setY(i, y * 0.9);
            deimosPositions.setZ(i, z * 1.1);
        }
        deimosGeometry.computeVertexNormals();
        const deimosMaterial = new THREE.MeshStandardMaterial({
            color: 0xc4b8a0, // Yellowish-tan like MRO image
            roughness: 1.0,
            metalness: 0.0,
            flatShading: true,
        });
        const deimos = new THREE.Mesh(deimosGeometry, deimosMaterial);
        const deimosOrbit = new THREE.Group();
        deimos.position.set(5.5, 0, 0);
        deimosOrbit.rotation.x = THREE.MathUtils.degToRad(25.19);
        deimosOrbit.add(deimos);
        scene.add(deimosOrbit);

        // Atmosphere
        const atmosphereGeometry = new THREE.SphereGeometry(3.35, 32, 32);
        const atmosphereMaterial = new THREE.MeshStandardMaterial({
            color: 0xff9966,
            transparent: true,
            opacity: 0.06,
            side: THREE.BackSide,
        });
        const atmosphere = new THREE.Mesh(atmosphereGeometry, atmosphereMaterial);
        scene.add(atmosphere);

        // Outer glow
        const glowGeometry = new THREE.SphereGeometry(3.5, 32, 32);
        const glowMaterial = new THREE.MeshBasicMaterial({
            color: 0xcc6644,
            transparent: true,
            opacity: 0.04,
            side: THREE.BackSide,
        });
        const glow = new THREE.Mesh(glowGeometry, glowMaterial);
        scene.add(glow);

        // Animation
        let animationId: number;
        const animate = () => {
            animationId = requestAnimationFrame(animate);

            // Mars rotation (1 Mars day = ~24.6 hours)
            mars.rotation.y += 0.002;

            // Phobos orbits Mars in 7.66 hours (very fast!)
            phobosOrbit.rotation.y += 0.008;

            // Deimos orbits Mars in 30.3 hours (slower than Mars rotates)
            deimosOrbit.rotation.y += 0.002;

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
            marsGeometry.dispose();
            marsMaterial.dispose();
            phobosGeometry.dispose();
            phobosMaterial.dispose();
            deimosGeometry.dispose();
            deimosMaterial.dispose();
            atmosphereGeometry.dispose();
            atmosphereMaterial.dispose();
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
