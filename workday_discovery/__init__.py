"""
Workday Tenant Discovery Engine

A multi-strategy discovery system for finding and validating
Workday career site tenants for large-scale job ingestion.
"""

from .models import WorkdayTenant, DiscoveryConfig, ValidationResult
from .discovery_engine import WorkdayTenantDiscoveryEngine
from .validator import TenantValidator
from .registry import TenantRegistry
from .scheduler import WorkdayIngestionScheduler

__all__ = [
    "WorkdayTenant",
    "DiscoveryConfig",
    "ValidationResult",
    "WorkdayTenantDiscoveryEngine",
    "TenantValidator",
    "TenantRegistry",
    "WorkdayIngestionScheduler",
]

__version__ = "1.0.0"
