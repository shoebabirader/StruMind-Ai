"""
Custom exceptions for StruMind Backend
"""

from typing import Any, Dict, Optional


class StrumindException(Exception):
    """Base exception for StruMind application"""
    
    def __init__(
        self,
        detail: str,
        status_code: int = 500,
        error_code: str = "STRUMIND_ERROR",
        headers: Optional[Dict[str, Any]] = None,
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        self.headers = headers
        super().__init__(detail)


class ValidationError(StrumindException):
    """Validation error"""
    
    def __init__(self, detail: str, field: Optional[str] = None):
        super().__init__(
            detail=detail,
            status_code=422,
            error_code="VALIDATION_ERROR"
        )
        self.field = field


class AuthenticationError(StrumindException):
    """Authentication error"""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            detail=detail,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(StrumindException):
    """Authorization error"""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            detail=detail,
            status_code=403,
            error_code="AUTHORIZATION_ERROR"
        )


class NotFoundError(StrumindException):
    """Resource not found error"""
    
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            detail=detail,
            status_code=404,
            error_code="NOT_FOUND_ERROR"
        )


class ConflictError(StrumindException):
    """Resource conflict error"""
    
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(
            detail=detail,
            status_code=409,
            error_code="CONFLICT_ERROR"
        )


class ComputationError(StrumindException):
    """Structural computation error"""
    
    def __init__(self, detail: str = "Computation failed"):
        super().__init__(
            detail=detail,
            status_code=422,
            error_code="COMPUTATION_ERROR"
        )


class ModelError(StrumindException):
    """Structural model error"""
    
    def __init__(self, detail: str = "Invalid structural model"):
        super().__init__(
            detail=detail,
            status_code=422,
            error_code="MODEL_ERROR"
        )


class AnalysisError(StrumindException):
    """Structural analysis error"""
    
    def __init__(self, detail: str = "Analysis failed"):
        super().__init__(
            detail=detail,
            status_code=422,
            error_code="ANALYSIS_ERROR"
        )


class DesignError(StrumindException):
    """Structural design error"""
    
    def __init__(self, detail: str = "Design failed"):
        super().__init__(
            detail=detail,
            status_code=422,
            error_code="DESIGN_ERROR"
        )


class ExportError(StrumindException):
    """Export/Import error"""
    
    def __init__(self, detail: str = "Export/Import failed"):
        super().__init__(
            detail=detail,
            status_code=422,
            error_code="EXPORT_ERROR"
        )