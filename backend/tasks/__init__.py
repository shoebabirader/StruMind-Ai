"""
Background tasks module for StruMind Backend
"""

from .celery_app import celery_app

__all__ = ["celery_app"]