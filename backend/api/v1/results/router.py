"""
Results & Visualization API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import json

from db.database import get_db
from db.models.analysis import AnalysisCase, AnalysisStatus
from db.models.design import DesignResult
from db.models.project import Project
from db.models.user import User
from api.v1.auth.router import get_current_user
from core.exceptions import ValidationError, NotFoundError

router = APIRouter()

# Pydantic models
from pydantic import BaseModel

class ResultsExportRequest(BaseModel):
    format: str  # "json", "csv", "pdf", "ifc", "gltf"
    analysis_ids: Optional[List[str]] = None
    design_result_ids: Optional[List[str]] = None
    include_geometry: bool = True
    include_loads: bool = True
    include_results: bool = True

class VisualizationRequest(BaseModel):
    analysis_id: Optional[str] = None
    result_type: str  # "displacement", "stress", "force", "mode_shape"
    scale_factor: float = 1.0
    component: Optional[str] = None  # "x", "y", "z", "magnitude"

class VisualizationResponse(BaseModel):
    visualization_data: Dict[str, Any]
    metadata: Dict[str, Any]
    scale_info: Dict[str, float]

def verify_project_access(project_id: UUID, current_user: User, db: Session):
    """Verify user has access to project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
    return project

@router.get("/health")
async def results_health():
    """Results service health check"""
    return {"status": "healthy", "service": "results"}

@router.get("/{project_id}/visualization", response_model=VisualizationResponse)
async def get_visualization_data(
    project_id: UUID,
    result_type: str = "displacement",
    analysis_id: Optional[str] = None,
    scale_factor: float = 1.0,
    component: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get visualization data for analysis results"""
    project = verify_project_access(project_id, current_user, db)
    
    # Generate visualization data based on result type
    visualization_data = {}
    metadata = {}
    scale_info = {}
    
    if result_type == "displacement":
        # Simulate displacement visualization data
        visualization_data = {
            "nodes": [
                {"id": "1", "x": 0.0, "y": 0.0, "z": 0.0, "dx": 0.001, "dy": 0.002, "dz": 0.0},
                {"id": "2", "x": 5.0, "y": 0.0, "z": 0.0, "dx": 0.003, "dy": 0.004, "dz": 0.0},
                {"id": "3", "x": 10.0, "y": 0.0, "z": 0.0, "dx": 0.002, "dy": 0.003, "dz": 0.0}
            ],
            "max_displacement": 0.004,
            "scale_factor": scale_factor
        }
        metadata = {
            "units": "m",
            "component": component or "magnitude",
            "result_type": result_type
        }
        scale_info = {
            "max_value": 0.004,
            "min_value": 0.0,
            "scale_factor": scale_factor
        }
    
    elif result_type == "stress":
        # Simulate stress visualization data
        visualization_data = {
            "elements": [
                {"id": "1", "stress": 150.5, "color": [1.0, 0.5, 0.0]},
                {"id": "2", "stress": 200.3, "color": [1.0, 0.0, 0.0]},
                {"id": "3", "stress": 120.8, "color": [0.5, 1.0, 0.0]}
            ],
            "max_stress": 200.3,
            "min_stress": 120.8
        }
        metadata = {
            "units": "MPa",
            "stress_type": "von_mises",
            "result_type": result_type
        }
        scale_info = {
            "max_value": 200.3,
            "min_value": 120.8,
            "scale_factor": 1.0
        }
    
    elif result_type == "mode_shape":
        # Simulate mode shape visualization data
        visualization_data = {
            "mode_number": 1,
            "frequency": 2.45,
            "nodes": [
                {"id": "1", "x": 0.0, "y": 0.0, "z": 0.0, "dx": 0.0, "dy": 0.1, "dz": 0.0},
                {"id": "2", "x": 5.0, "y": 0.0, "z": 0.0, "dx": 0.0, "dy": 0.8, "dz": 0.0},
                {"id": "3", "x": 10.0, "y": 0.0, "z": 0.0, "dx": 0.0, "dy": 1.0, "dz": 0.0}
            ],
            "scale_factor": scale_factor
        }
        metadata = {
            "frequency": 2.45,
            "units": "Hz",
            "mode_number": 1,
            "mass_participation": 0.85
        }
        scale_info = {
            "max_value": 1.0,
            "min_value": 0.0,
            "scale_factor": scale_factor
        }
    
    return VisualizationResponse(
        visualization_data=visualization_data,
        metadata=metadata,
        scale_info=scale_info
    )

@router.post("/{project_id}/export")
async def export_results(
    project_id: UUID,
    export_request: ResultsExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export analysis and design results"""
    project = verify_project_access(project_id, current_user, db)
    
    export_data = {
        "project_id": str(project_id),
        "project_name": project.name,
        "export_timestamp": datetime.utcnow().isoformat(),
        "format": export_request.format
    }
    
    # Include analysis results if requested
    if export_request.analysis_ids:
        analyses = db.query(AnalysisCase).filter(
            AnalysisCase.id.in_([UUID(aid) for aid in export_request.analysis_ids]),
            AnalysisCase.project_id == project_id
        ).all()
        
        export_data["analyses"] = [
            {
                "id": str(analysis.id),
                "type": analysis.analysis_type,
                "status": analysis.status,
                "results": analysis.results,
                "created_at": analysis.created_at.isoformat()
            }
            for analysis in analyses
        ]
    
    # Include design results if requested
    if export_request.design_result_ids:
        design_results = db.query(DesignResult).filter(
            DesignResult.id.in_([UUID(did) for did in export_request.design_result_ids]),
            DesignResult.project_id == project_id
        ).all()
        
        export_data["design_results"] = [
            {
                "id": str(result.id),
                "element_id": str(result.element_id),
                "design_code": result.design_code,
                "status": result.status,
                "results": result.results,
                "utilization_ratio": result.utilization_ratio,
                "created_at": result.created_at.isoformat()
            }
            for result in design_results
        ]
    
    # Handle different export formats
    if export_request.format == "json":
        return Response(
            content=json.dumps(export_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=project_{project_id}_results.json"}
        )
    
    elif export_request.format == "ifc":
        # Simulate IFC export
        ifc_content = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('project_export.ifc','2024-01-01T00:00:00',('StruMind'),('StruMind Platform'),'StruMind IFC Exporter','StruMind','');
FILE_SCHEMA(('IFC4'));
ENDSEC;

DATA;
#1= IFCPROJECT('3rNg_N5O94$BKpvYUsBZZA',$,'StruMind Project',$,$,$,$,(#2),#3);
#2= IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#4,$);
#3= IFCUNITASSIGNMENT((#5,#6,#7));
#4= IFCAXIS2PLACEMENT3D(#8,$,$);
#5= IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);
#6= IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#7= IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);
#8= IFCCARTESIANPOINT((0.,0.,0.));
ENDSEC;

END-ISO-10303-21;"""
        
        return Response(
            content=ifc_content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename=project_{project_id}_model.ifc"}
        )
    
    else:
        return {"message": f"Export format {export_request.format} processed", "data": export_data}

@router.get("/{project_id}/summary")
async def get_project_results_summary(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive results summary for project"""
    project = verify_project_access(project_id, current_user, db)
    
    # Get analysis summary
    analyses = db.query(AnalysisCase).filter(AnalysisCase.project_id == project_id).all()
    analysis_summary = {
        "total": len(analyses),
        "completed": len([a for a in analyses if a.status == AnalysisStatus.COMPLETED]),
        "failed": len([a for a in analyses if a.status == AnalysisStatus.FAILED]),
        "pending": len([a for a in analyses if a.status == AnalysisStatus.PENDING])
    }
    
    # Get design summary
    design_results = db.query(DesignResult).filter(DesignResult.project_id == project_id).all()
    design_summary = {
        "total": len(design_results),
        "passed": len([d for d in design_results if str(d.status) == "PASSED"]),
        "failed": len([d for d in design_results if str(d.status) == "FAILED"]),
        "pending": len([d for d in design_results if str(d.status) == "PENDING"])
    }
    
    # Calculate utilization statistics
    utilizations = [d.utilization_ratio for d in design_results if d.utilization_ratio is not None]
    utilization_stats = {
        "max": max(utilizations) if utilizations else 0.0,
        "avg": sum(utilizations) / len(utilizations) if utilizations else 0.0,
        "min": min(utilizations) if utilizations else 0.0
    }
    
    return {
        "project_id": str(project_id),
        "project_name": project.name,
        "analysis_summary": analysis_summary,
        "design_summary": design_summary,
        "utilization_stats": utilization_stats,
        "last_updated": datetime.utcnow().isoformat()
    }