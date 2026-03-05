"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Mesh } from "three";

function ShelfBlock({ position, color }: { position: [number, number, number]; color: string }) {
  const ref = useRef<Mesh>(null);
  useFrame((state) => {
    if (!ref.current) return;
    ref.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.6 + position[0]) * 0.18;
  });

  return (
    <mesh ref={ref} position={position}>
      <boxGeometry args={[0.7, 0.7, 0.7]} />
      <meshStandardMaterial color={color} roughness={0.35} metalness={0.45} />
    </mesh>
  );
}

export function DataShelf3D() {
  return (
    <div className="card h-52 w-full overflow-hidden">
      <Canvas dpr={[1, 1.4]} camera={{ position: [0, 1.2, 4.4], fov: 45 }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[3, 4, 3]} intensity={2.2} color="#7fd4ff" />
        <pointLight position={[-4, 2, -2]} intensity={1.2} color="#37b5ff" />

        <ShelfBlock position={[-1.3, 0, 0]} color="#37b5ff" />
        <ShelfBlock position={[0, 0.35, 0]} color="#35d39d" />
        <ShelfBlock position={[1.3, -0.2, 0]} color="#ffc857" />

        <mesh position={[0, -0.8, 0]}>
          <boxGeometry args={[4.6, 0.15, 1.8]} />
          <meshStandardMaterial color="#19314d" roughness={0.8} metalness={0.1} />
        </mesh>
      </Canvas>
    </div>
  );
}
