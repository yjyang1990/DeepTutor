# -*- coding: utf-8 -*-
"""
Qdrant Vector Database Service.

Provides vector storage and retrieval capabilities.
"""

from .client import QdrantService, MockQdrantClient


__all__ = [
    "QdrantService",
    "MockQdrantClient",
]
