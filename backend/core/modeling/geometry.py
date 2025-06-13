"""
Geometry engine for 3D structural modeling
"""

import math
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from dataclasses import dataclass

from core.exceptions import ModelError


@dataclass
class Point3D:
    """3D point representation"""
    x: float
    y: float
    z: float
    
    def __add__(self, other: 'Point3D') -> 'Point3D':
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Point3D') -> 'Point3D':
        return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Point3D':
        return Point3D(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def distance_to(self, other: 'Point3D') -> float:
        """Calculate distance to another point"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array"""
        return np.array([self.x, self.y, self.z])


@dataclass
class Vector3D:
    """3D vector representation"""
    x: float
    y: float
    z: float
    
    @classmethod
    def from_points(cls, start: Point3D, end: Point3D) -> 'Vector3D':
        """Create vector from two points"""
        return cls(end.x - start.x, end.y - start.y, end.z - start.z)
    
    def magnitude(self) -> float:
        """Calculate vector magnitude"""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def normalize(self) -> 'Vector3D':
        """Return normalized vector"""
        mag = self.magnitude()
        if mag == 0:
            raise ModelError("Cannot normalize zero vector")
        return Vector3D(self.x / mag, self.y / mag, self.z / mag)
    
    def dot(self, other: 'Vector3D') -> float:
        """Dot product with another vector"""
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other: 'Vector3D') -> 'Vector3D':
        """Cross product with another vector"""
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def angle_to(self, other: 'Vector3D') -> float:
        """Calculate angle to another vector in radians"""
        dot_product = self.dot(other)
        magnitudes = self.magnitude() * other.magnitude()
        if magnitudes == 0:
            return 0.0
        cos_angle = dot_product / magnitudes
        # Clamp to avoid numerical errors
        cos_angle = max(-1.0, min(1.0, cos_angle))
        return math.acos(cos_angle)
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array"""
        return np.array([self.x, self.y, self.z])


class Transform3D:
    """3D transformation matrix operations"""
    
    def __init__(self, matrix: Optional[np.ndarray] = None):
        if matrix is None:
            self.matrix = np.eye(4)  # Identity matrix
        else:
            if matrix.shape != (4, 4):
                raise ModelError("Transformation matrix must be 4x4")
            self.matrix = matrix.copy()
    
    @classmethod
    def translation(cls, dx: float, dy: float, dz: float) -> 'Transform3D':
        """Create translation transformation"""
        matrix = np.eye(4)
        matrix[0, 3] = dx
        matrix[1, 3] = dy
        matrix[2, 3] = dz
        return cls(matrix)
    
    @classmethod
    def rotation_x(cls, angle: float) -> 'Transform3D':
        """Create rotation around X-axis (angle in radians)"""
        matrix = np.eye(4)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        matrix[1, 1] = cos_a
        matrix[1, 2] = -sin_a
        matrix[2, 1] = sin_a
        matrix[2, 2] = cos_a
        return cls(matrix)
    
    @classmethod
    def rotation_y(cls, angle: float) -> 'Transform3D':
        """Create rotation around Y-axis (angle in radians)"""
        matrix = np.eye(4)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        matrix[0, 0] = cos_a
        matrix[0, 2] = sin_a
        matrix[2, 0] = -sin_a
        matrix[2, 2] = cos_a
        return cls(matrix)
    
    @classmethod
    def rotation_z(cls, angle: float) -> 'Transform3D':
        """Create rotation around Z-axis (angle in radians)"""
        matrix = np.eye(4)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        matrix[0, 0] = cos_a
        matrix[0, 1] = -sin_a
        matrix[1, 0] = sin_a
        matrix[1, 1] = cos_a
        return cls(matrix)
    
    @classmethod
    def scale(cls, sx: float, sy: float, sz: float) -> 'Transform3D':
        """Create scaling transformation"""
        matrix = np.eye(4)
        matrix[0, 0] = sx
        matrix[1, 1] = sy
        matrix[2, 2] = sz
        return cls(matrix)
    
    def __mul__(self, other: 'Transform3D') -> 'Transform3D':
        """Multiply transformations"""
        return Transform3D(self.matrix @ other.matrix)
    
    def transform_point(self, point: Point3D) -> Point3D:
        """Transform a point"""
        homogeneous = np.array([point.x, point.y, point.z, 1.0])
        transformed = self.matrix @ homogeneous
        return Point3D(transformed[0], transformed[1], transformed[2])
    
    def transform_vector(self, vector: Vector3D) -> Vector3D:
        """Transform a vector (ignores translation)"""
        homogeneous = np.array([vector.x, vector.y, vector.z, 0.0])
        transformed = self.matrix @ homogeneous
        return Vector3D(transformed[0], transformed[1], transformed[2])
    
    def inverse(self) -> 'Transform3D':
        """Get inverse transformation"""
        try:
            inv_matrix = np.linalg.inv(self.matrix)
            return Transform3D(inv_matrix)
        except np.linalg.LinAlgError:
            raise ModelError("Transformation matrix is not invertible")


class CoordinateSystem:
    """Local coordinate system definition"""
    
    def __init__(self, origin: Point3D, x_axis: Vector3D, y_axis: Vector3D, z_axis: Vector3D):
        self.origin = origin
        self.x_axis = x_axis.normalize()
        self.y_axis = y_axis.normalize()
        self.z_axis = z_axis.normalize()
        
        # Verify orthogonality
        if abs(self.x_axis.dot(self.y_axis)) > 1e-10:
            raise ModelError("X and Y axes must be orthogonal")
        if abs(self.y_axis.dot(self.z_axis)) > 1e-10:
            raise ModelError("Y and Z axes must be orthogonal")
        if abs(self.z_axis.dot(self.x_axis)) > 1e-10:
            raise ModelError("Z and X axes must be orthogonal")
    
    @classmethod
    def from_two_points(cls, start: Point3D, end: Point3D, up_vector: Vector3D = None) -> 'CoordinateSystem':
        """Create coordinate system from two points"""
        if up_vector is None:
            up_vector = Vector3D(0, 0, 1)  # Default Z-up
        
        x_axis = Vector3D.from_points(start, end).normalize()
        z_axis = up_vector.normalize()
        
        # Ensure Z is perpendicular to X
        z_axis = z_axis - x_axis * z_axis.dot(x_axis)
        z_axis = z_axis.normalize()
        
        y_axis = z_axis.cross(x_axis).normalize()
        
        return cls(start, x_axis, y_axis, z_axis)
    
    def to_global_transform(self) -> Transform3D:
        """Get transformation from local to global coordinates"""
        matrix = np.eye(4)
        matrix[0, 0:3] = self.x_axis.to_array()
        matrix[1, 0:3] = self.y_axis.to_array()
        matrix[2, 0:3] = self.z_axis.to_array()
        matrix[0:3, 3] = self.origin.to_array()
        return Transform3D(matrix)
    
    def to_local_transform(self) -> Transform3D:
        """Get transformation from global to local coordinates"""
        return self.to_global_transform().inverse()


class GeometryEngine:
    """Main geometry engine for structural modeling"""
    
    @staticmethod
    def calculate_element_length(start: Point3D, end: Point3D) -> float:
        """Calculate element length"""
        return start.distance_to(end)
    
    @staticmethod
    def calculate_element_direction_cosines(start: Point3D, end: Point3D) -> Tuple[float, float, float]:
        """Calculate direction cosines of element"""
        vector = Vector3D.from_points(start, end).normalize()
        return (vector.x, vector.y, vector.z)
    
    @staticmethod
    def calculate_element_local_axes(start: Point3D, end: Point3D, orientation_angle: float = 0.0) -> CoordinateSystem:
        """Calculate local coordinate system for element"""
        # Local X-axis along element
        x_axis = Vector3D.from_points(start, end).normalize()
        
        # Determine local Y and Z axes
        if abs(x_axis.z) < 0.9:
            # Element is not vertical
            temp_z = Vector3D(0, 0, 1)
            y_axis = temp_z.cross(x_axis).normalize()
            z_axis = x_axis.cross(y_axis).normalize()
        else:
            # Element is vertical
            temp_y = Vector3D(0, 1, 0)
            z_axis = x_axis.cross(temp_y).normalize()
            y_axis = z_axis.cross(x_axis).normalize()
        
        # Apply orientation angle rotation about local X-axis
        if orientation_angle != 0.0:
            rotation = Transform3D.rotation_x(orientation_angle)
            y_axis = rotation.transform_vector(y_axis)
            z_axis = rotation.transform_vector(z_axis)
        
        return CoordinateSystem(start, x_axis, y_axis, z_axis)
    
    @staticmethod
    def point_on_line(start: Point3D, end: Point3D, parameter: float) -> Point3D:
        """Get point on line at parameter t (0.0 to 1.0)"""
        if not (0.0 <= parameter <= 1.0):
            raise ModelError("Parameter must be between 0.0 and 1.0")
        
        vector = Vector3D.from_points(start, end)
        return start + Point3D(vector.x * parameter, vector.y * parameter, vector.z * parameter)
    
    @staticmethod
    def project_point_to_line(point: Point3D, line_start: Point3D, line_end: Point3D) -> Tuple[Point3D, float]:
        """Project point onto line, return projected point and parameter"""
        line_vector = Vector3D.from_points(line_start, line_end)
        point_vector = Vector3D.from_points(line_start, point)
        
        line_length_sq = line_vector.magnitude() ** 2
        if line_length_sq == 0:
            return line_start, 0.0
        
        parameter = point_vector.dot(line_vector) / line_length_sq
        projected_point = GeometryEngine.point_on_line(line_start, line_end, max(0.0, min(1.0, parameter)))
        
        return projected_point, parameter
    
    @staticmethod
    def calculate_bounding_box(points: List[Point3D]) -> Tuple[Point3D, Point3D]:
        """Calculate bounding box for list of points"""
        if not points:
            raise ModelError("Cannot calculate bounding box for empty point list")
        
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')
        
        for point in points:
            min_x = min(min_x, point.x)
            min_y = min(min_y, point.y)
            min_z = min(min_z, point.z)
            max_x = max(max_x, point.x)
            max_y = max(max_y, point.y)
            max_z = max(max_z, point.z)
        
        return Point3D(min_x, min_y, min_z), Point3D(max_x, max_y, max_z)
    
    @staticmethod
    def snap_to_grid(point: Point3D, grid_size: float) -> Point3D:
        """Snap point to grid"""
        if grid_size <= 0:
            return point
        
        return Point3D(
            round(point.x / grid_size) * grid_size,
            round(point.y / grid_size) * grid_size,
            round(point.z / grid_size) * grid_size
        )
    
    @staticmethod
    def find_nearest_point(target: Point3D, candidates: List[Point3D], tolerance: float = 1e-6) -> Optional[Point3D]:
        """Find nearest point from candidates within tolerance"""
        nearest_point = None
        min_distance = float('inf')
        
        for candidate in candidates:
            distance = target.distance_to(candidate)
            if distance < min_distance and distance <= tolerance:
                min_distance = distance
                nearest_point = candidate
        
        return nearest_point
    
    @staticmethod
    def are_points_collinear(p1: Point3D, p2: Point3D, p3: Point3D, tolerance: float = 1e-10) -> bool:
        """Check if three points are collinear"""
        v1 = Vector3D.from_points(p1, p2)
        v2 = Vector3D.from_points(p1, p3)
        
        cross_product = v1.cross(v2)
        return cross_product.magnitude() < tolerance
    
    @staticmethod
    def calculate_centroid(points: List[Point3D]) -> Point3D:
        """Calculate centroid of points"""
        if not points:
            raise ModelError("Cannot calculate centroid for empty point list")
        
        sum_x = sum_y = sum_z = 0.0
        for point in points:
            sum_x += point.x
            sum_y += point.y
            sum_z += point.z
        
        n = len(points)
        return Point3D(sum_x / n, sum_y / n, sum_z / n)