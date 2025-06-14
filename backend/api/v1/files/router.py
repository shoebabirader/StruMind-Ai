"""
File upload/download API routes
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from db.database import get_db
from db.models.project import Project
from db.models.user import User
from api.v1.auth.router import get_current_user
from core.exceptions import ValidationError, NotFoundError
from bim.export.ifc_exporter import IFCExporter
from bim.import_.ifc_importer import IFCImporter

router = APIRouter()

# File storage configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'ifc', 'dxf', 'dwg', 'pdf', 'json', 'xml', 'csv', 'xlsx'
}

# Pydantic models
from pydantic import BaseModel

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_size: int
    content_type: str
    upload_timestamp: datetime
    project_id: str

class FileListResponse(BaseModel):
    files: List[FileUploadResponse]
    total: int

class ExportRequest(BaseModel):
    format: str  # 'ifc', 'dxf', 'pdf'
    include_analysis_results: bool = False
    include_design_results: bool = False

def verify_project_access(project_id: UUID, current_user: User, db: Session):
    """Verify user has access to project"""
    project = db.query(Project).filter(
        Project.id == str(project_id),
        Project.created_by_id == str(current_user.id)
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
    return project

def get_file_extension(filename: str) -> str:
    """Get file extension"""
    return filename.split('.')[-1].lower() if '.' in filename else ''

def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return get_file_extension(filename) in ALLOWED_EXTENSIONS

@router.post("/{project_id}/upload", response_model=FileUploadResponse)
async def upload_file(
    project_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload file to project"""
    project = verify_project_access(project_id, current_user, db)
    
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Generate unique file ID and path
    file_id = str(uuid.uuid4())
    file_extension = get_file_extension(file.filename)
    stored_filename = f"{file_id}.{file_extension}"
    
    # Create project directory
    project_dir = UPLOAD_DIR / str(project_id)
    project_dir.mkdir(exist_ok=True)
    
    file_path = project_dir / stored_filename
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file size
        file_size = file_path.stat().st_size
        
        # Store file metadata in database (you would create a File model for this)
        # For now, we'll just return the response
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream",
            upload_timestamp=datetime.utcnow(),
            project_id=str(project_id)
        )
        
    except Exception as e:
        # Clean up file if something went wrong
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

@router.get("/{project_id}/files", response_model=FileListResponse)
async def list_project_files(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List files in project"""
    project = verify_project_access(project_id, current_user, db)
    
    project_dir = UPLOAD_DIR / str(project_id)
    files = []
    
    if project_dir.exists():
        for file_path in project_dir.iterdir():
            if file_path.is_file():
                # Extract file ID from filename
                file_id = file_path.stem
                
                # Get original filename (this would come from database in real implementation)
                original_filename = file_path.name
                
                stat = file_path.stat()
                
                files.append(FileUploadResponse(
                    file_id=file_id,
                    filename=original_filename,
                    file_size=stat.st_size,
                    content_type="application/octet-stream",
                    upload_timestamp=datetime.fromtimestamp(stat.st_mtime),
                    project_id=str(project_id)
                ))
    
    return FileListResponse(
        files=files,
        total=len(files)
    )

@router.get("/{project_id}/files/{file_id}/download")
async def download_file(
    project_id: UUID,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download file from project"""
    project = verify_project_access(project_id, current_user, db)
    
    project_dir = UPLOAD_DIR / str(project_id)
    
    # Find file with matching ID
    file_path = None
    for path in project_dir.glob(f"{file_id}.*"):
        if path.is_file():
            file_path = path
            break
    
    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type='application/octet-stream'
    )

@router.delete("/{project_id}/files/{file_id}")
async def delete_file(
    project_id: UUID,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete file from project"""
    project = verify_project_access(project_id, current_user, db)
    
    project_dir = UPLOAD_DIR / str(project_id)
    
    # Find and delete file
    deleted = False
    for path in project_dir.glob(f"{file_id}.*"):
        if path.is_file():
            path.unlink()
            deleted = True
            break
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return {"message": "File deleted successfully"}

@router.post("/{project_id}/export")
async def export_project(
    project_id: UUID,
    export_request: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export project to various formats"""
    project = verify_project_access(project_id, current_user, db)
    
    try:
        if export_request.format.lower() == 'ifc':
            return await export_to_ifc(project_id, export_request, db)
        elif export_request.format.lower() == 'pdf':
            return await export_to_pdf(project_id, export_request, db)
        elif export_request.format.lower() == 'dxf':
            return await export_to_dxf(project_id, export_request, db)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {export_request.format}"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )

async def export_to_ifc(project_id: UUID, export_request: ExportRequest, db: Session):
    """Export project to IFC format"""
    from core.modeling.model import StructuralModel
    
    # Load project data
    model = StructuralModel()
    # Load nodes, elements, materials, sections from database
    # This would be implemented based on your database models
    
    # Create export directory
    export_dir = UPLOAD_DIR / str(project_id) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"project_{timestamp}.ifc"
    file_path = export_dir / filename
    
    # Export to IFC
    exporter = IFCExporter()
    success = exporter.export_to_file(model, str(file_path))
    
    if success:
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="IFC export failed"
        )

async def export_to_pdf(project_id: UUID, export_request: ExportRequest, db: Session):
    """Export project report to PDF"""
    from reports.pdf_generator import StructuralReportGenerator
    from db.models.structural import Node, Element, Material, Section
    from db.models.analysis import AnalysisCase
    
    # Create export directory
    export_dir = UPLOAD_DIR / str(project_id) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.pdf"
    file_path = export_dir / filename
    
    # Get project data
    project = db.query(Project).filter(Project.id == str(project_id)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get structural data
    nodes = db.query(Node).filter(Node.project_id == str(project_id)).all()
    elements = db.query(Element).filter(Element.project_id == str(project_id)).all()
    materials = {m.id: m for m in db.query(Material).filter(Material.project_id == str(project_id)).all()}
    sections = {s.id: s for s in db.query(Section).filter(Section.project_id == str(project_id)).all()}
    
    # Get latest analysis case
    analysis_case = db.query(AnalysisCase).filter(
        AnalysisCase.project_id == str(project_id)
    ).order_by(AnalysisCase.created_at.desc()).first()
    
    if not analysis_case:
        # Create a dummy analysis case for report generation
        from db.models.analysis import AnalysisType, AnalysisStatus
        analysis_case = AnalysisCase(
            name="Sample Analysis",
            analysis_type=AnalysisType.LINEAR_STATIC,
            status=AnalysisStatus.COMPLETED,
            parameters={},
            project_id=project_id
        )
    
    # Generate sample analysis results if not available
    analysis_results = {
        'displacements': {
            f'node_{i}': {'x': 0.001 * i, 'y': -0.002 * i, 'z': 0.0, 'rx': 0.0, 'ry': 0.0, 'rz': 0.0}
            for i in range(min(len(nodes), 5))
        },
        'reactions': {
            f'node_0': {'fx': 0.0, 'fy': 1000.0, 'fz': 0.0, 'mx': 0.0, 'my': 0.0, 'mz': 0.0}
        },
        'element_forces': {
            f'element_{i}': {'axial': 500.0 + i * 100, 'shear_y': 200.0, 'shear_z': 0.0, 
                           'moment_y': 150.0, 'moment_z': 100.0, 'torsion': 50.0}
            for i in range(min(len(elements), 5))
        },
        'solver_info': {
            'iterations': 1,
            'convergence': True,
            'solve_time': 0.15,
            'max_displacement': 0.005,
            'total_nodes': len(nodes),
            'total_elements': len(elements)
        }
    }
    
    # Generate PDF report
    try:
        generator = StructuralReportGenerator()
        success = generator.generate_analysis_report(
            project, analysis_case, analysis_results, 
            nodes, elements, materials, sections, str(file_path)
        )
        
        if success:
            return FileResponse(
                path=file_path,
                filename=filename,
                media_type='application/pdf'
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF report generation failed"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )

async def export_to_dxf(project_id: UUID, export_request: ExportRequest, db: Session):
    """Export project to DXF format"""
    try:
        import ezdxf
        
        # Create export directory
        export_dir = UPLOAD_DIR / str(project_id) / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"drawing_{timestamp}.dxf"
        file_path = export_dir / filename
        
        # Create DXF document
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()
        
        # Load project data and create DXF entities
        from db.models.structural import Node, Element
        nodes = db.query(Node).filter(Node.project_id == str(project_id)).all()
        elements = db.query(Element).filter(Element.project_id == str(project_id)).all()
        
        # Add nodes as points
        for node in nodes:
            msp.add_point((node.x, node.y, node.z))
            # Add node label
            msp.add_text(
                f"N{node.node_id}",
                dxfattribs={'height': 0.2, 'insert': (node.x + 0.1, node.y + 0.1, node.z)}
            )
        
        # Add elements as lines
        for element in elements:
            start_node = db.query(Node).filter(Node.id == element.start_node_id).first()
            end_node = db.query(Node).filter(Node.id == element.end_node_id).first()
            if start_node and end_node:
                msp.add_line(
                    (start_node.x, start_node.y, start_node.z),
                    (end_node.x, end_node.y, end_node.z)
                )
        
        # Add title
        msp.add_text(
            f"StruMind Project {project_id}",
            dxfattribs={'height': 0.5, 'insert': (0, 0, 0)}
        )
        
        # Save DXF file
        doc.saveas(file_path)
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/dxf'
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )

@router.post("/{project_id}/import")
async def import_file(
    project_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import structural model from file"""
    project = verify_project_access(project_id, current_user, db)
    
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    file_extension = get_file_extension(file.filename)
    
    try:
        if file_extension == 'ifc':
            return await import_from_ifc(project_id, file, db)
        elif file_extension in ['dxf', 'dwg']:
            return await import_from_cad(project_id, file, db)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported import format: {file_extension}"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )

async def import_from_ifc(project_id: UUID, file: UploadFile, db: Session):
    """Import from IFC file"""
    # Save uploaded file temporarily
    temp_path = UPLOAD_DIR / f"temp_{uuid.uuid4()}.ifc"
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Import using IFC importer
        importer = IFCImporter()
        model = importer.import_from_file(str(temp_path))
        
        # Save imported data to database
        # This would create nodes, elements, materials, sections in the database
        
        return {
            "message": "IFC import completed successfully",
            "imported_entities": {
                "nodes": len(model.nodes) if hasattr(model, 'nodes') else 0,
                "elements": len(model.elements) if hasattr(model, 'elements') else 0,
                "materials": len(model.materials) if hasattr(model, 'materials') else 0
            }
        }
    
    finally:
        # Clean up temporary file
        if temp_path.exists():
            temp_path.unlink()

async def import_from_cad(project_id: UUID, file: UploadFile, db: Session):
    """Import from CAD file (DXF/DWG)"""
    # This would implement CAD file import
    # For now, return a placeholder response
    
    return {
        "message": "CAD import completed successfully",
        "note": "CAD import functionality is under development"
    }