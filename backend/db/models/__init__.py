"""
Database models for StruMind Backend
"""

from .user import User, Organization, OrganizationMember
from .project import Project, ProjectMember
from .structural import (
    Node,
    Element,
    Material,
    Section,
    Load,
    LoadCase,
    LoadCombination,
    BoundaryCondition,
    Release,
)
from .analysis import (
    AnalysisCase,
    AnalysisResult,
    NodeResult,
    ElementResult,
    ModalResult,
)
from .design import (
    DesignCase,
    DesignResult,
    ReinforcementDetail,
    ConnectionDetail,
)
from .bim import BIMModel, BIMElement, BIMProperty

__all__ = [
    # User & Organization
    "User",
    "Organization", 
    "OrganizationMember",
    # Project
    "Project",
    "ProjectMember",
    # Structural
    "Node",
    "Element",
    "Material",
    "Section",
    "Load",
    "LoadCase",
    "LoadCombination",
    "BoundaryCondition",
    "Release",
    # Analysis
    "AnalysisCase",
    "AnalysisResult",
    "NodeResult",
    "ElementResult",
    "ModalResult",
    # Design
    "DesignCase",
    "DesignResult",
    "ReinforcementDetail",
    "ConnectionDetail",
    # BIM
    "BIMModel",
    "BIMElement",
    "BIMProperty",
]