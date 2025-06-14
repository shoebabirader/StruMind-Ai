/**
 * 3D Model Viewer Component using React Three Fiber
 * Displays structural models with interactive controls
 */

import React, { useRef, useState, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Grid, Text, Line } from '@react-three/drei';
import * as THREE from 'three';
import { Vector3, BufferGeometry, Float32BufferAttribute } from 'three';

interface Node {
  id: string;
  x: number;
  y: number;
  z: number;
  label?: string;
}

interface Element {
  id: string;
  startNodeId: string;
  endNodeId: string;
  elementType: string;
  color?: string;
}

interface ModelViewer3DProps {
  nodes: Node[];
  elements: Element[];
  showGrid?: boolean;
  showLabels?: boolean;
  deformedShape?: boolean;
  displacements?: Record<string, { x: number; y: number; z: number }>;
  stresses?: Record<string, number>;
  onNodeSelect?: (nodeId: string) => void;
  onElementSelect?: (elementId: string) => void;
}

const NodeComponent: React.FC<{
  node: Node;
  isSelected: boolean;
  onClick: () => void;
  displacement?: { x: number; y: number; z: number };
}> = ({ node, isSelected, onClick, displacement }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  
  const position = displacement 
    ? [node.x + displacement.x, node.y + displacement.y, node.z + displacement.z]
    : [node.x, node.y, node.z];

  return (
    <group position={position as [number, number, number]}>
      <mesh ref={meshRef} onClick={onClick}>
        <sphereGeometry args={[0.05, 8, 8]} />
        <meshStandardMaterial 
          color={isSelected ? '#ff6b6b' : '#4ecdc4'} 
          transparent
          opacity={0.8}
        />
      </mesh>
      {node.label && (
        <Text
          position={[0, 0.1, 0]}
          fontSize={0.05}
          color="black"
          anchorX="center"
          anchorY="middle"
        >
          {node.label}
        </Text>
      )}
    </group>
  );
};

const ElementComponent: React.FC<{
  element: Element;
  startNode: Node;
  endNode: Node;
  isSelected: boolean;
  onClick: () => void;
  displacements?: Record<string, { x: number; y: number; z: number }>;
  deformationScale?: number;
  viewMode?: string;
  stress?: number;
}> = ({ element, startNode, endNode, isSelected, onClick, displacements, deformationScale = 1, viewMode = 'wireframe', stress }) => {
  const lineRef = useRef<any>(null);
  
  const startDisp = displacements?.[startNode.id];
  const startPos = startDisp 
    ? [
        startNode.x + startDisp.x * deformationScale,
        startNode.y + startDisp.y * deformationScale,
        startNode.z + startDisp.z * deformationScale
      ]
    : [startNode.x, startNode.y, startNode.z];
    
  const endDisp = displacements?.[endNode.id];
  const endPos = endDisp
    ? [
        endNode.x + endDisp.x * deformationScale,
        endNode.y + endDisp.y * deformationScale,
        endNode.z + endDisp.z * deformationScale
      ]
    : [endNode.x, endNode.y, endNode.z];

  const points = [
    new Vector3(...startPos as [number, number, number]),
    new Vector3(...endPos as [number, number, number])
  ];

  const getElementColor = () => {
    if (isSelected) return '#ff6b6b';
    
    // Stress-based coloring
    if (viewMode === 'stress' && stress !== undefined) {
      return getStressColor(stress);
    }
    
    // Displacement-based coloring
    if (viewMode === 'displacement' && (startDisp || endDisp)) {
      const maxDisp = Math.max(
        startDisp ? Math.sqrt(startDisp.x**2 + startDisp.y**2 + startDisp.z**2) : 0,
        endDisp ? Math.sqrt(endDisp.x**2 + endDisp.y**2 + endDisp.z**2) : 0
      );
      return getDisplacementColor(maxDisp);
    }
    
    if (element.color) return element.color;
    
    switch (element.elementType) {
      case 'beam': return '#45b7d1';
      case 'column': return '#96ceb4';
      case 'brace': return '#feca57';
      default: return '#95a5a6';
    }
  };

  const getStressColor = (stress: number) => {
    // Normalize stress to 0-1 range (assuming max stress of 250 MPa)
    const normalized = Math.min(Math.abs(stress) / 250, 1);
    
    if (normalized < 0.2) return '#00ff00'; // Green - low stress
    if (normalized < 0.4) return '#80ff00'; // Yellow-green
    if (normalized < 0.6) return '#ffff00'; // Yellow
    if (normalized < 0.8) return '#ff8000'; // Orange
    return '#ff0000'; // Red - high stress
  };

  const getDisplacementColor = (displacement: number) => {
    // Normalize displacement to 0-1 range (assuming max displacement of 0.01 m)
    const normalized = Math.min(displacement / 0.01, 1);
    
    if (normalized < 0.2) return '#0000ff'; // Blue - low displacement
    if (normalized < 0.4) return '#0080ff'; // Light blue
    if (normalized < 0.6) return '#00ffff'; // Cyan
    if (normalized < 0.8) return '#80ff80'; // Light green
    return '#ff0000'; // Red - high displacement
  };

  return (
    <Line
      ref={lineRef}
      points={points}
      color={getElementColor()}
      lineWidth={isSelected ? 4 : 2}
      onClick={onClick}
    />
  );
};

const ModelScene: React.FC<{
  nodes: Node[];
  elements: Element[];
  selectedNodeId: string | null;
  selectedElementId: string | null;
  onNodeSelect: (nodeId: string) => void;
  onElementSelect: (elementId: string) => void;
  displacements?: Record<string, { x: number; y: number; z: number }>;
  stresses?: Record<string, number>;
  showGrid: boolean;
  showLabels: boolean;
  deformationScale: number;
  viewMode: string;
}> = ({ 
  nodes, 
  elements, 
  selectedNodeId, 
  selectedElementId, 
  onNodeSelect, 
  onElementSelect,
  displacements,
  stresses,
  showGrid,
  showLabels,
  deformationScale,
  viewMode
}) => {
  const { camera } = useThree();
  
  useEffect(() => {
    // Auto-fit camera to model
    if (nodes.length > 0) {
      const bounds = {
        minX: Math.min(...nodes.map(n => n.x)),
        maxX: Math.max(...nodes.map(n => n.x)),
        minY: Math.min(...nodes.map(n => n.y)),
        maxY: Math.max(...nodes.map(n => n.y)),
        minZ: Math.min(...nodes.map(n => n.z)),
        maxZ: Math.max(...nodes.map(n => n.z))
      };
      
      const center = new Vector3(
        (bounds.minX + bounds.maxX) / 2,
        (bounds.minY + bounds.maxY) / 2,
        (bounds.minZ + bounds.maxZ) / 2
      );
      
      const size = Math.max(
        bounds.maxX - bounds.minX,
        bounds.maxY - bounds.minY,
        bounds.maxZ - bounds.minZ
      );
      
      camera.position.set(
        center.x + size,
        center.y + size,
        center.z + size
      );
      camera.lookAt(center);
    }
  }, [nodes, camera]);

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.6} />
      <directionalLight position={[10, 10, 5]} intensity={0.8} />
      <directionalLight position={[-10, -10, -5]} intensity={0.4} />
      
      {/* Grid */}
      {showGrid && (
        <Grid
          args={[20, 20]}
          cellSize={1}
          cellThickness={0.5}
          cellColor="#6f6f6f"
          sectionSize={5}
          sectionThickness={1}
          sectionColor="#9d4edd"
          fadeDistance={30}
          fadeStrength={1}
          followCamera={false}
          infiniteGrid={true}
        />
      )}
      
      {/* Nodes */}
      {nodes.map(node => (
        <NodeComponent
          key={node.id}
          node={node}
          isSelected={selectedNodeId === node.id}
          onClick={() => onNodeSelect(node.id)}
          displacement={displacements?.[node.id] ? {
            x: displacements[node.id].x * deformationScale,
            y: displacements[node.id].y * deformationScale,
            z: displacements[node.id].z * deformationScale
          } : undefined}
        />
      ))}
      
      {/* Elements */}
      {elements.map(element => {
        const startNode = nodes.find(n => n.id === element.startNodeId);
        const endNode = nodes.find(n => n.id === element.endNodeId);
        
        if (!startNode || !endNode) return null;
        
        return (
          <ElementComponent
            key={element.id}
            element={element}
            startNode={startNode}
            endNode={endNode}
            isSelected={selectedElementId === element.id}
            onClick={() => onElementSelect(element.id)}
            displacements={displacements}
            deformationScale={deformationScale}
            viewMode={viewMode}
            stress={stresses?.[element.id]}
          />
        );
      })}
    </>
  );
};

const ModelViewer3D: React.FC<ModelViewer3DProps> = ({
  nodes,
  elements,
  showGrid: initialShowGrid = true,
  showLabels: initialShowLabels = true,
  deformedShape: initialDeformedShape = false,
  displacements,
  stresses,
  onNodeSelect,
  onElementSelect
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);
  const [showGrid, setShowGrid] = useState(initialShowGrid);
  const [showLabels, setShowLabels] = useState(initialShowLabels);
  const [deformedShape, setDeformedShape] = useState(initialDeformedShape);
  const [deformationScale, setDeformationScale] = useState(10);
  const [viewMode, setViewMode] = useState('wireframe');

  const handleNodeSelect = (nodeId: string) => {
    setSelectedNodeId(nodeId);
    setSelectedElementId(null);
    onNodeSelect?.(nodeId);
  };

  const handleElementSelect = (elementId: string) => {
    setSelectedElementId(elementId);
    setSelectedNodeId(null);
    onElementSelect?.(elementId);
  };

  return (
    <div className="w-full h-full bg-gray-100">
      <Canvas
        camera={{ position: [10, 10, 10], fov: 60 }}
        style={{ background: 'linear-gradient(to bottom, #87CEEB, #f0f8ff)' }}
      >
        <ModelScene
          nodes={nodes}
          elements={elements}
          selectedNodeId={selectedNodeId}
          selectedElementId={selectedElementId}
          onNodeSelect={handleNodeSelect}
          onElementSelect={handleElementSelect}
          displacements={deformedShape ? displacements : undefined}
          stresses={stresses}
          showGrid={showGrid}
          showLabels={showLabels}
          deformationScale={deformationScale}
          viewMode={viewMode}
        />
        <OrbitControls
          enablePan={true}
          enableZoom={true}
          enableRotate={true}
          dampingFactor={0.05}
          screenSpacePanning={false}
        />
      </Canvas>
      
      {/* Controls Panel */}
      <div className="absolute top-4 left-4 bg-white p-4 rounded-lg shadow-lg max-w-xs">
        <h3 className="font-semibold mb-2">View Controls</h3>
        <div className="space-y-2">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={showGrid}
              onChange={(e) => setShowGrid(e.target.checked)}
              className="mr-2"
            />
            Show Grid
          </label>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={showLabels}
              onChange={(e) => setShowLabels(e.target.checked)}
              className="mr-2"
            />
            Show Labels
          </label>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={deformedShape}
              onChange={(e) => setDeformedShape(e.target.checked)}
              className="mr-2"
            />
            Deformed Shape
          </label>
          <div className="mt-4">
            <label className="block text-sm font-medium mb-1">
              Deformation Scale
            </label>
            <input
              type="range"
              min="1"
              max="100"
              value={deformationScale}
              onChange={(e) => setDeformationScale(Number(e.target.value))}
              className="w-full"
              disabled={!deformedShape}
            />
            <span className="text-xs text-gray-500">{deformationScale}x</span>
          </div>
          <div className="mt-4">
            <label className="block text-sm font-medium mb-1">
              View Mode
            </label>
            <select
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value)}
              className="w-full p-1 border rounded"
            >
              <option value="wireframe">Wireframe</option>
              <option value="solid">Solid</option>
              <option value="stress">Stress Contour</option>
              <option value="displacement">Displacement Contour</option>
            </select>
          </div>
        </div>
      </div>
      
      {/* Selection Info */}
      {(selectedNodeId || selectedElementId) && (
        <div className="absolute bottom-4 left-4 bg-white p-4 rounded-lg shadow-lg">
          <h3 className="font-semibold mb-2">Selection Info</h3>
          {selectedNodeId && (
            <div>
              <p><strong>Node:</strong> {selectedNodeId}</p>
              {/* Add more node details */}
            </div>
          )}
          {selectedElementId && (
            <div>
              <p><strong>Element:</strong> {selectedElementId}</p>
              {/* Add more element details */}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ModelViewer3D;