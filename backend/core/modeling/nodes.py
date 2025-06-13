"""
Node management for StruMind structural modeling
"""

from typing import Dict, List, Optional, Tuple, Any
import uuid
import numpy as np
from pydantic import BaseModel, Field

from .geometry import Point3D, Vector3D


class Node(BaseModel):
    """Structural node definition"""
    id: str = Field(default_factory=lambda: f"N_{uuid.uuid4().hex[:8]}")
    x: float
    y: float
    z: float
    description: Optional[str] = None
    is_active: bool = True
    
    # Node properties
    mass: float = 0.0  # Lumped mass at node
    temperature: float = 20.0  # Temperature for thermal analysis
    
    # Coordinate system
    local_coordinate_system: Optional[Dict[str, List[float]]] = None
    
    def get_coordinates(self) -> Tuple[float, float, float]:
        """Get node coordinates as tuple"""
        return (self.x, self.y, self.z)
    
    def get_point3d(self) -> Point3D:
        """Get node coordinates as Point3D"""
        return Point3D(x=self.x, y=self.y, z=self.z)
    
    def distance_to(self, other: 'Node') -> float:
        """Calculate distance to another node"""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return (dx**2 + dy**2 + dz**2)**0.5
    
    def move_to(self, x: float, y: float, z: float):
        """Move node to new coordinates"""
        self.x = x
        self.y = y
        self.z = z
    
    def translate(self, dx: float, dy: float, dz: float):
        """Translate node by given offsets"""
        self.x += dx
        self.y += dy
        self.z += dz


class NodeManager:
    """Manager for structural nodes"""
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self._tolerance = 1e-6  # Tolerance for duplicate node detection
    
    def add_node(self, x: float, y: float, z: float, node_id: str = None,
                description: str = None, check_duplicates: bool = True) -> Node:
        """Add a node to the model"""
        
        # Check for duplicate coordinates if requested
        if check_duplicates:
            existing_node = self.find_node_at_coordinates(x, y, z)
            if existing_node:
                return existing_node
        
        # Generate ID if not provided
        if node_id is None:
            node_id = f"N_{len(self.nodes) + 1:04d}"
        
        # Check if ID already exists
        if node_id in self.nodes:
            raise ValueError(f"Node with ID {node_id} already exists")
        
        # Create node
        node = Node(
            id=node_id,
            x=x,
            y=y,
            z=z,
            description=description
        )
        
        self.nodes[node_id] = node
        return node
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the model"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            return True
        return False
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID"""
        return self.nodes.get(node_id)
    
    def node_exists(self, node_id: str) -> bool:
        """Check if node exists"""
        return node_id in self.nodes
    
    def find_node_at_coordinates(self, x: float, y: float, z: float) -> Optional[Node]:
        """Find node at given coordinates (within tolerance)"""
        for node in self.nodes.values():
            distance = ((node.x - x)**2 + (node.y - y)**2 + (node.z - z)**2)**0.5
            if distance < self._tolerance:
                return node
        return None
    
    def find_nodes_in_region(self, min_x: float, max_x: float,
                           min_y: float, max_y: float,
                           min_z: float, max_z: float) -> List[Node]:
        """Find nodes within a rectangular region"""
        nodes_in_region = []
        for node in self.nodes.values():
            if (min_x <= node.x <= max_x and
                min_y <= node.y <= max_y and
                min_z <= node.z <= max_z):
                nodes_in_region.append(node)
        return nodes_in_region
    
    def find_nodes_near_point(self, x: float, y: float, z: float, radius: float) -> List[Node]:
        """Find nodes within a given radius of a point"""
        nodes_near = []
        for node in self.nodes.values():
            distance = ((node.x - x)**2 + (node.y - y)**2 + (node.z - z)**2)**0.5
            if distance <= radius:
                nodes_near.append(node)
        return nodes_near
    
    def update_node_coordinates(self, node_id: str, x: float, y: float, z: float) -> bool:
        """Update node coordinates"""
        if node_id in self.nodes:
            self.nodes[node_id].move_to(x, y, z)
            return True
        return False
    
    def translate_nodes(self, node_ids: List[str], dx: float, dy: float, dz: float) -> int:
        """Translate multiple nodes"""
        count = 0
        for node_id in node_ids:
            if node_id in self.nodes:
                self.nodes[node_id].translate(dx, dy, dz)
                count += 1
        return count
    
    def get_model_bounds(self) -> Dict[str, float]:
        """Get bounding box of all nodes"""
        if not self.nodes:
            return {
                "min_x": 0, "max_x": 0,
                "min_y": 0, "max_y": 0,
                "min_z": 0, "max_z": 0
            }
        
        x_coords = [node.x for node in self.nodes.values()]
        y_coords = [node.y for node in self.nodes.values()]
        z_coords = [node.z for node in self.nodes.values()]
        
        return {
            "min_x": min(x_coords),
            "max_x": max(x_coords),
            "min_y": min(y_coords),
            "max_y": max(y_coords),
            "min_z": min(z_coords),
            "max_z": max(z_coords)
        }
    
    def get_center_of_mass(self) -> Tuple[float, float, float]:
        """Get center of mass of all nodes"""
        if not self.nodes:
            return (0.0, 0.0, 0.0)
        
        total_mass = sum(node.mass for node in self.nodes.values())
        
        if total_mass > 0:
            # Weighted by mass
            cx = sum(node.x * node.mass for node in self.nodes.values()) / total_mass
            cy = sum(node.y * node.mass for node in self.nodes.values()) / total_mass
            cz = sum(node.z * node.mass for node in self.nodes.values()) / total_mass
        else:
            # Geometric center
            cx = sum(node.x for node in self.nodes.values()) / len(self.nodes)
            cy = sum(node.y for node in self.nodes.values()) / len(self.nodes)
            cz = sum(node.z for node in self.nodes.values()) / len(self.nodes)
        
        return (cx, cy, cz)
    
    def generate_grid_nodes(self, origin: Tuple[float, float, float],
                          spacing: Tuple[float, float, float],
                          count: Tuple[int, int, int],
                          prefix: str = "GRID") -> List[Node]:
        """Generate a grid of nodes"""
        nodes = []
        ox, oy, oz = origin
        sx, sy, sz = spacing
        nx, ny, nz = count
        
        for i in range(nx):
            for j in range(ny):
                for k in range(nz):
                    x = ox + i * sx
                    y = oy + j * sy
                    z = oz + k * sz
                    
                    node_id = f"{prefix}_{i+1:02d}_{j+1:02d}_{k+1:02d}"
                    node = self.add_node(x, y, z, node_id, check_duplicates=False)
                    nodes.append(node)
        
        return nodes
    
    def generate_line_nodes(self, start: Tuple[float, float, float],
                          end: Tuple[float, float, float],
                          num_nodes: int, prefix: str = "LINE") -> List[Node]:
        """Generate nodes along a line"""
        nodes = []
        x1, y1, z1 = start
        x2, y2, z2 = end
        
        for i in range(num_nodes):
            t = i / (num_nodes - 1) if num_nodes > 1 else 0
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            z = z1 + t * (z2 - z1)
            
            node_id = f"{prefix}_{i+1:03d}"
            node = self.add_node(x, y, z, node_id, check_duplicates=False)
            nodes.append(node)
        
        return nodes
    
    def generate_circle_nodes(self, center: Tuple[float, float, float],
                            radius: float, num_nodes: int,
                            normal: Tuple[float, float, float] = (0, 0, 1),
                            prefix: str = "CIRCLE") -> List[Node]:
        """Generate nodes in a circle"""
        nodes = []
        cx, cy, cz = center
        nx, ny, nz = normal
        
        # Normalize normal vector
        norm = (nx**2 + ny**2 + nz**2)**0.5
        if norm > 0:
            nx, ny, nz = nx/norm, ny/norm, nz/norm
        
        # Create two perpendicular vectors in the plane
        if abs(nz) < 0.9:
            u1, u2, u3 = 0, nz, -ny
        else:
            u1, u2, u3 = ny, -nx, 0
        
        # Normalize u
        norm_u = (u1**2 + u2**2 + u3**2)**0.5
        if norm_u > 0:
            u1, u2, u3 = u1/norm_u, u2/norm_u, u3/norm_u
        
        # Create v = n × u
        v1 = ny * u3 - nz * u2
        v2 = nz * u1 - nx * u3
        v3 = nx * u2 - ny * u1
        
        # Generate nodes
        for i in range(num_nodes):
            angle = 2 * np.pi * i / num_nodes
            cos_a, sin_a = np.cos(angle), np.sin(angle)
            
            x = cx + radius * (cos_a * u1 + sin_a * v1)
            y = cy + radius * (cos_a * u2 + sin_a * v2)
            z = cz + radius * (cos_a * u3 + sin_a * v3)
            
            node_id = f"{prefix}_{i+1:03d}"
            node = self.add_node(x, y, z, node_id, check_duplicates=False)
            nodes.append(node)
        
        return nodes
    
    def merge_duplicate_nodes(self, tolerance: float = None) -> int:
        """Merge nodes that are within tolerance of each other"""
        if tolerance is None:
            tolerance = self._tolerance
        
        nodes_to_remove = []
        merge_count = 0
        
        node_list = list(self.nodes.values())
        
        for i, node1 in enumerate(node_list):
            if node1.id in nodes_to_remove:
                continue
                
            for j, node2 in enumerate(node_list[i+1:], i+1):
                if node2.id in nodes_to_remove:
                    continue
                
                distance = node1.distance_to(node2)
                if distance < tolerance:
                    # Keep node1, remove node2
                    nodes_to_remove.append(node2.id)
                    merge_count += 1
        
        # Remove duplicate nodes
        for node_id in nodes_to_remove:
            self.remove_node(node_id)
        
        return merge_count
    
    def get_node_statistics(self) -> Dict[str, Any]:
        """Get statistics about nodes"""
        if not self.nodes:
            return {"count": 0}
        
        bounds = self.get_model_bounds()
        center = self.get_center_of_mass()
        
        # Calculate distances from center
        distances = []
        for node in self.nodes.values():
            dist = ((node.x - center[0])**2 + 
                   (node.y - center[1])**2 + 
                   (node.z - center[2])**2)**0.5
            distances.append(dist)
        
        return {
            "count": len(self.nodes),
            "bounds": bounds,
            "center_of_mass": center,
            "max_distance_from_center": max(distances) if distances else 0,
            "min_distance_from_center": min(distances) if distances else 0,
            "average_distance_from_center": sum(distances) / len(distances) if distances else 0,
            "total_mass": sum(node.mass for node in self.nodes.values()),
            "active_nodes": sum(1 for node in self.nodes.values() if node.is_active)
        }
    
    def clear_all_nodes(self):
        """Remove all nodes"""
        self.nodes.clear()
    
    def set_tolerance(self, tolerance: float):
        """Set tolerance for duplicate node detection"""
        self._tolerance = tolerance
    
    def export_nodes_to_list(self) -> List[Dict[str, Any]]:
        """Export all nodes to list format"""
        return [node.dict() for node in self.nodes.values()]
    
    def import_nodes_from_list(self, nodes_data: List[Dict[str, Any]]) -> int:
        """Import nodes from list format"""
        count = 0
        for node_data in nodes_data:
            try:
                node = Node(**node_data)
                if node.id not in self.nodes:
                    self.nodes[node.id] = node
                    count += 1
            except Exception as e:
                print(f"Error importing node: {e}")
        
        return count


class NodeValidator:
    """Node validation utilities"""
    
    @staticmethod
    def validate_node(node: Node) -> List[str]:
        """Validate a single node"""
        errors = []
        
        # Check coordinates are finite
        if not all(np.isfinite([node.x, node.y, node.z])):
            errors.append(f"Node {node.id} has invalid coordinates")
        
        # Check mass is non-negative
        if node.mass < 0:
            errors.append(f"Node {node.id} has negative mass")
        
        return errors
    
    @staticmethod
    def validate_node_set(nodes: Dict[str, Node]) -> List[str]:
        """Validate a set of nodes"""
        errors = []
        
        # Validate individual nodes
        for node in nodes.values():
            node_errors = NodeValidator.validate_node(node)
            errors.extend(node_errors)
        
        # Check for duplicate coordinates
        coordinates = {}
        tolerance = 1e-6
        
        for node in nodes.values():
            coord_key = (round(node.x/tolerance), round(node.y/tolerance), round(node.z/tolerance))
            if coord_key in coordinates:
                errors.append(f"Nodes {coordinates[coord_key]} and {node.id} have duplicate coordinates")
            else:
                coordinates[coord_key] = node.id
        
        return errors