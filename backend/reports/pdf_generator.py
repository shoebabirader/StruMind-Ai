"""
Advanced PDF report generator for structural analysis results
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import numpy as np

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import black, blue, red, green, orange, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus import Image as ReportLabImage
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Line, Rect, Circle
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF

from db.models.analysis import AnalysisCase, AnalysisType
from db.models.project import Project
from db.models.structural import Node, Element, Material, Section


class StructuralReportGenerator:
    """
    Comprehensive PDF report generator for structural analysis
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=blue
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=blue
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=12,
            textColor=black
        ))
    
    def generate_analysis_report(self, project: Project, analysis_case: AnalysisCase,
                               analysis_results: Dict[str, Any], nodes: List[Node],
                               elements: List[Element], materials: Dict[str, Material],
                               sections: Dict[str, Section], output_path: str) -> bool:
        """
        Generate comprehensive structural analysis report
        """
        try:
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=20*mm,
                bottomMargin=20*mm
            )
            
            story = []
            
            # Title page
            story.extend(self._create_title_page(project, analysis_case))
            story.append(PageBreak())
            
            # Executive summary
            story.extend(self._create_executive_summary(analysis_case, analysis_results))
            story.append(PageBreak())
            
            # Project information
            story.extend(self._create_project_info(project, nodes, elements, materials, sections))
            story.append(PageBreak())
            
            # Analysis setup
            story.extend(self._create_analysis_setup(analysis_case))
            story.append(PageBreak())
            
            # Results section
            story.extend(self._create_results_section(analysis_results, analysis_case.analysis_type))
            story.append(PageBreak())
            
            # Design checks (if applicable)
            story.extend(self._create_design_section(analysis_results))
            
            # Build PDF
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"Error generating PDF report: {str(e)}")
            return False
    
    def _create_title_page(self, project: Project, analysis_case: AnalysisCase) -> List:
        """Create title page"""
        story = []
        
        # Main title
        title = Paragraph("STRUCTURAL ANALYSIS REPORT", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 30))
        
        # Project name
        project_title = Paragraph(f"Project: {project.name}", self.styles['Heading2'])
        story.append(project_title)
        story.append(Spacer(1, 20))
        
        # Analysis type
        analysis_title = Paragraph(f"Analysis Type: {analysis_case.analysis_type.value}", self.styles['Heading3'])
        story.append(analysis_title)
        story.append(Spacer(1, 40))
        
        # Project details table
        project_data = [
            ['Project ID:', str(project.id)],
            ['Project Description:', project.description or 'N/A'],
            ['Analysis Case:', analysis_case.name],
            ['Analysis Date:', analysis_case.created_at.strftime('%Y-%m-%d %H:%M:%S')],
            ['Report Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Generated By:', 'StruMind Analysis Engine v1.0']
        ]
        
        project_table = Table(project_data, colWidths=[40*mm, 100*mm])
        project_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), blue),
            ('TEXTCOLOR', (0, 0), (0, -1), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), white),
            ('TEXTCOLOR', (1, 0), (1, -1), black),
            ('GRID', (0, 0), (-1, -1), 1, black)
        ]))
        
        story.append(project_table)
        story.append(Spacer(1, 60))
        
        # Disclaimer
        disclaimer = Paragraph(
            "<b>DISCLAIMER:</b> This report has been generated by StruMind structural analysis software. "
            "The results should be reviewed by a qualified structural engineer before use in design or construction.",
            self.styles['Normal']
        )
        story.append(disclaimer)
        
        return story
    
    def _create_executive_summary(self, analysis_case: AnalysisCase, results: Dict[str, Any]) -> List:
        """Create executive summary"""
        story = []
        
        story.append(Paragraph("1. EXECUTIVE SUMMARY", self.styles['SectionHeader']))
        story.append(Spacer(1, 12))
        
        # Analysis overview
        overview_text = f"""
        This report presents the results of a {analysis_case.analysis_type.value} analysis 
        performed on the structural model. The analysis was completed successfully with 
        convergence achieved within acceptable tolerances.
        """
        story.append(Paragraph(overview_text, self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Key results summary
        solver_info = results.get('solver_info', {})
        
        summary_data = [
            ['Analysis Type:', analysis_case.analysis_type.value],
            ['Convergence:', 'Yes' if solver_info.get('convergence', False) else 'No'],
            ['Solution Time:', f"{solver_info.get('solve_time', 0):.3f} seconds"],
            ['Total Nodes:', str(solver_info.get('total_nodes', 0))],
            ['Total Elements:', str(solver_info.get('total_elements', 0))],
            ['Max Displacement:', f"{solver_info.get('max_displacement', 0):.6f} m"]
        ]
        
        summary_table = Table(summary_data, colWidths=[50*mm, 80*mm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), blue),
            ('TEXTCOLOR', (0, 0), (0, -1), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, black)
        ]))
        
        story.append(summary_table)
        
        return story
    
    def _create_project_info(self, project: Project, nodes: List[Node], 
                           elements: List[Element], materials: Dict[str, Material],
                           sections: Dict[str, Section]) -> List:
        """Create project information section"""
        story = []
        
        story.append(Paragraph("2. PROJECT INFORMATION", self.styles['SectionHeader']))
        story.append(Spacer(1, 12))
        
        # Model statistics
        story.append(Paragraph("2.1 Model Statistics", self.styles['SubHeader']))
        
        stats_data = [
            ['Total Nodes:', str(len(nodes))],
            ['Total Elements:', str(len(elements))],
            ['Total Materials:', str(len(materials))],
            ['Total Sections:', str(len(sections))],
            ['Model Units:', 'SI (m, N, Pa)']
        ]
        
        stats_table = Table(stats_data, colWidths=[50*mm, 50*mm])
        stats_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, black)
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # Model bounds
        if nodes:
            x_coords = [node.x for node in nodes]
            y_coords = [node.y for node in nodes]
            z_coords = [node.z for node in nodes]
            
            story.append(Paragraph("2.2 Model Bounds", self.styles['SubHeader']))
            
            bounds_data = [
                ['X Range:', f"{min(x_coords):.3f} to {max(x_coords):.3f} m"],
                ['Y Range:', f"{min(y_coords):.3f} to {max(y_coords):.3f} m"],
                ['Z Range:', f"{min(z_coords):.3f} to {max(z_coords):.3f} m"]
            ]
            
            bounds_table = Table(bounds_data, colWidths=[50*mm, 80*mm])
            bounds_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, black)
            ]))
            
            story.append(bounds_table)
        
        return story
    
    def _create_analysis_setup(self, analysis_case: AnalysisCase) -> List:
        """Create analysis setup section"""
        story = []
        
        story.append(Paragraph("3. ANALYSIS SETUP", self.styles['SectionHeader']))
        story.append(Spacer(1, 12))
        
        # Analysis parameters
        story.append(Paragraph("3.1 Analysis Parameters", self.styles['SubHeader']))
        
        parameters = analysis_case.parameters or {}
        
        param_data = [
            ['Analysis Type:', analysis_case.analysis_type.value],
            ['Analysis Name:', analysis_case.name],
            ['Description:', analysis_case.description or 'N/A']
        ]
        
        # Add specific parameters based on analysis type
        if analysis_case.analysis_type == AnalysisType.MODAL:
            param_data.append(['Number of Modes:', str(parameters.get('num_modes', 10))])
        elif analysis_case.analysis_type == AnalysisType.RESPONSE_SPECTRUM:
            param_data.append(['Spectrum Scale:', str(parameters.get('spectrum_scale', 1.0))])
        elif analysis_case.analysis_type == AnalysisType.TIME_HISTORY:
            param_data.append(['Time Step:', f"{parameters.get('time_step', 0.01)} s"])
            param_data.append(['Duration:', f"{parameters.get('duration', 10.0)} s"])
        
        param_table = Table(param_data, colWidths=[60*mm, 80*mm])
        param_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, black)
        ]))
        
        story.append(param_table)
        
        return story
    
    def _create_results_section(self, results: Dict[str, Any], analysis_type: AnalysisType) -> List:
        """Create results section"""
        story = []
        
        story.append(Paragraph("4. ANALYSIS RESULTS", self.styles['SectionHeader']))
        story.append(Spacer(1, 12))
        
        if analysis_type == AnalysisType.LINEAR_STATIC:
            story.extend(self._create_static_results(results))
        elif analysis_type == AnalysisType.MODAL:
            story.extend(self._create_modal_results(results))
        elif analysis_type == AnalysisType.RESPONSE_SPECTRUM:
            story.extend(self._create_response_spectrum_results(results))
        elif analysis_type == AnalysisType.TIME_HISTORY:
            story.extend(self._create_time_history_results(results))
        
        return story
    
    def _create_static_results(self, results: Dict[str, Any]) -> List:
        """Create static analysis results"""
        story = []
        
        # Displacement results
        story.append(Paragraph("4.1 Displacement Results", self.styles['SubHeader']))
        
        displacements = results.get('displacements', {})
        if displacements:
            # Create displacement summary table
            disp_data = [['Node', 'UX (m)', 'UY (m)', 'UZ (m)', 'RX (rad)', 'RY (rad)', 'RZ (rad)']]
            
            for node_id, disp in list(displacements.items())[:10]:  # Show first 10 nodes
                disp_data.append([
                    node_id,
                    f"{disp.get('x', 0):.6f}",
                    f"{disp.get('y', 0):.6f}",
                    f"{disp.get('z', 0):.6f}",
                    f"{disp.get('rx', 0):.6f}",
                    f"{disp.get('ry', 0):.6f}",
                    f"{disp.get('rz', 0):.6f}"
                ])
            
            disp_table = Table(disp_data, colWidths=[25*mm, 20*mm, 20*mm, 20*mm, 20*mm, 20*mm, 20*mm])
            disp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, black)
            ]))
            
            story.append(disp_table)
            story.append(Spacer(1, 12))
        
        # Reaction results
        story.append(Paragraph("4.2 Reaction Forces", self.styles['SubHeader']))
        
        reactions = results.get('reactions', {})
        if reactions:
            react_data = [['Node', 'FX (N)', 'FY (N)', 'FZ (N)', 'MX (N·m)', 'MY (N·m)', 'MZ (N·m)']]
            
            for node_id, react in reactions.items():
                react_data.append([
                    node_id,
                    f"{react.get('fx', 0):.2f}",
                    f"{react.get('fy', 0):.2f}",
                    f"{react.get('fz', 0):.2f}",
                    f"{react.get('mx', 0):.2f}",
                    f"{react.get('my', 0):.2f}",
                    f"{react.get('mz', 0):.2f}"
                ])
            
            react_table = Table(react_data, colWidths=[25*mm, 20*mm, 20*mm, 20*mm, 20*mm, 20*mm, 20*mm])
            react_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, black)
            ]))
            
            story.append(react_table)
            story.append(Spacer(1, 12))
        
        # Element forces
        story.append(Paragraph("4.3 Element Forces", self.styles['SubHeader']))
        
        element_forces = results.get('element_forces', {})
        if element_forces:
            force_data = [['Element', 'Axial (N)', 'Shear Y (N)', 'Shear Z (N)', 'Moment Y (N·m)', 'Moment Z (N·m)', 'Torsion (N·m)']]
            
            for elem_id, forces in list(element_forces.items())[:10]:  # Show first 10 elements
                force_data.append([
                    elem_id,
                    f"{forces.get('axial', 0):.2f}",
                    f"{forces.get('shear_y', 0):.2f}",
                    f"{forces.get('shear_z', 0):.2f}",
                    f"{forces.get('moment_y', 0):.2f}",
                    f"{forces.get('moment_z', 0):.2f}",
                    f"{forces.get('torsion', 0):.2f}"
                ])
            
            force_table = Table(force_data, colWidths=[25*mm, 20*mm, 20*mm, 20*mm, 20*mm, 20*mm, 20*mm])
            force_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, black)
            ]))
            
            story.append(force_table)
        
        return story
    
    def _create_modal_results(self, results: Dict[str, Any]) -> List:
        """Create modal analysis results"""
        story = []
        
        story.append(Paragraph("4.1 Modal Analysis Results", self.styles['SubHeader']))
        
        frequencies = results.get('frequencies', [])
        periods = results.get('periods', [])
        
        if frequencies and periods:
            modal_data = [['Mode', 'Frequency (Hz)', 'Period (s)']]
            
            for i, (freq, period) in enumerate(zip(frequencies, periods)):
                modal_data.append([
                    str(i + 1),
                    f"{freq:.3f}",
                    f"{period:.3f}"
                ])
            
            modal_table = Table(modal_data, colWidths=[30*mm, 40*mm, 40*mm])
            modal_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, black)
            ]))
            
            story.append(modal_table)
        
        return story
    
    def _create_response_spectrum_results(self, results: Dict[str, Any]) -> List:
        """Create response spectrum results"""
        story = []
        
        story.append(Paragraph("4.1 Response Spectrum Results", self.styles['SubHeader']))
        
        # Add response spectrum specific results
        spectrum_scale = results.get('spectrum_scale', 1.0)
        story.append(Paragraph(f"Spectrum Scale Factor: {spectrum_scale}", self.styles['Normal']))
        
        # Include modal results if available
        modal_results = results.get('modal_results', {})
        if modal_results:
            story.extend(self._create_modal_results(modal_results))
        
        return story
    
    def _create_time_history_results(self, results: Dict[str, Any]) -> List:
        """Create time history results"""
        story = []
        
        story.append(Paragraph("4.1 Time History Results", self.styles['SubHeader']))
        
        solver_info = results.get('solver_info', {})
        
        th_data = [
            ['Time Step:', f"{solver_info.get('time_step', 0.01)} s"],
            ['Duration:', f"{solver_info.get('duration', 10.0)} s"],
            ['Number of Steps:', str(solver_info.get('num_steps', 0))]
        ]
        
        th_table = Table(th_data, colWidths=[50*mm, 50*mm])
        th_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, black)
        ]))
        
        story.append(th_table)
        
        return story
    
    def _create_design_section(self, results: Dict[str, Any]) -> List:
        """Create design checks section"""
        story = []
        
        story.append(Paragraph("5. DESIGN CHECKS", self.styles['SectionHeader']))
        story.append(Spacer(1, 12))
        
        # Placeholder for design results
        design_text = """
        Design checks would be performed based on the analysis results and applicable design codes.
        This section would include:
        
        • Steel member design per AISC 360
        • Concrete member design per IS 456 or ACI 318
        • Connection design
        • Foundation design
        • Serviceability checks
        """
        
        story.append(Paragraph(design_text, self.styles['Normal']))
        
        return story