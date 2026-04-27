"""
Base model configuration for skawr-auth models.
Provides a flexible base that can work with different SQLAlchemy setups.
"""

from typing import Any, Optional
from sqlalchemy.ext.declarative import declarative_base

# Default base - can be overridden by projects
AuthBase: Any = None

def get_base(custom_base: Optional[Any] = None) -> Any:
    """
    Get the SQLAlchemy base class for auth models.

    Args:
        custom_base: Optional custom base class from the consuming project

    Returns:
        The base class to use for auth models
    """
    global AuthBase

    if custom_base is not None:
        AuthBase = custom_base
        return AuthBase

    if AuthBase is None:
        AuthBase = declarative_base()

    return AuthBase