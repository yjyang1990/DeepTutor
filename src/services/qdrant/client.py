# -*- coding: utf-8 -*-
"""
Qdrant Vector Database Service.

Provides vector storage and retrieval for:
- Evaluation rubrics
- Student profiles
- Learning analytics
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.logging import get_logger


logger = get_logger(__name__)


class QdrantService:
    """
    Qdrant vector database service.
    
    Provides:
    - Collection management
    - Vector upsert/delete
    - Similarity search
    - Payload filtering
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        collection_name: str = "default",
        vector_size: int = 1536,
        distance: str = "Cosine",
        api_key: Optional[str] = None,
    ):
        self.url = url
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        """Lazy-load the Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                self._client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                )
            except ImportError:
                logger.warning("qdrant-client not installed. Using mock client.")
                self._client = MockQdrantClient()
        return self._client

    async def create_collection(
        self,
        collection_name: Optional[str] = None,
        vector_size: Optional[int] = None,
        distance: Optional[str] = None,
    ) -> bool:
        """
        Create a collection.
        
        Args:
            collection_name: Optional override for default
            vector_size: Vector dimension (required for first creation)
            distance: Distance metric (Cosine, Euclid, Dot)
            
        Returns:
            True if created, False if already exists
        """
        name = collection_name or self.collection_name
        size = vector_size or self.vector_size
        dist = distance or self.distance
        
        try:
            # Check if exists
            collections = self.client.get_collections().collections
            if any(c.name == name for c in collections):
                logger.info(f"Collection {name} already exists")
                return False
            
            # Create
            distance_map = {
                "Cosine": "Cosine",
                "Euclid": "Euclid",
                "Dot": "Dot",
            }
            
            self.client.create_collection(
                collection_name=name,
                vectors_config={
                    "size": size,
                    "distance": distance_map.get(dist, "Cosine"),
                },
            )
            
            logger.info(f"Created collection: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False

    async def upsert(
        self,
        points: List[Dict[str, Any]],
        collection_name: Optional[str] = None,
    ) -> bool:
        """
        Upsert vectors with payloads.
        
        Args:
            points: List of {"id": str, "vector": List[float], "payload": dict}
            collection_name: Optional override
            
        Returns:
            True on success
        """
        name = collection_name or self.collection_name
        
        try:
            # Ensure collection exists
            await self.create_collection()
            
            # Format for Qdrant
            from qdrant_client.models import PointStruct, Vector, Payload
            
            qdrant_points = []
            for point in points:
                qdrant_points.append(PointStruct(
                    id=point["id"],
                    vector=point["vector"],
                    payload=point.get("payload", {}),
                ))
            
            self.client.upsert(
                collection_name=name,
                points=qdrant_points,
            )
            
            logger.debug(f"Upserted {len(points)} points to {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert: {e}")
            return False

    async def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filter_conditions: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: The query vector
            limit: Maximum results
            filter_conditions: Optional payload filters
            collection_name: Optional override
            
        Returns:
            List of {"id", "score", "payload"}
        """
        name = collection_name or self.collection_name
        
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            search_kwargs = {
                "collection_name": name,
                "query_vector": query_vector,
                "limit": limit,
            }
            
            if filter_conditions:
                # Build filter
                must_clauses = []
                for key, value in filter_conditions.items():
                    must_clauses.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
                
                search_kwargs["query_filter"] = Filter(must=must_clauses)
            
            results = self.client.search(**search_kwargs)
            
            return [
                {
                    "id": r.id,
                    "score": r.score,
                    "payload": r.payload or {},
                }
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def delete(
        self,
        point_ids: List[str],
        collection_name: Optional[str] = None,
    ) -> bool:
        """Delete points by ID."""
        name = collection_name or self.collection_name
        
        try:
            self.client.delete(
                collection_name=name,
                points_selector=point_ids,
            )
            logger.debug(f"Deleted {len(point_ids)} points from {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete: {e}")
            return False

    async def count(
        self,
        filter_conditions: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None,
    ) -> int:
        """Count points in collection."""
        name = collection_name or self.collection_name
        
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            kwargs = {"collection_name": name}
            
            if filter_conditions:
                must_clauses = []
                for key, value in filter_conditions.items():
                    must_clauses.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
                kwargs["query_filter"] = Filter(must=must_clauses)
            
            count = self.client.count(**kwargs)
            return count.count
            
        except Exception as e:
            logger.error(f"Count failed: {e}")
            return 0


class MockQdrantClient:
    """
    Mock Qdrant client for when qdrant-client is not installed.
    
    Useful for development and testing.
    """
    
    def __init__(self):
        self._collections: Dict[str, List[Dict[str, Any]]] = {}
    
    def get_collections(self):
        class Collections:
            def __init__(self, collections):
                self.collections = collections
        return Collections([
            type("Collection", (), {"name": name})()
            for name in self._collections.keys()
        ])
    
    def create_collection(self, collection_name: str, vectors_config: dict):
        if collection_name not in self._collections:
            self._collections[collection_name] = []
    
    def upsert(self, collection_name: str, points: List[Any]):
        if collection_name not in self._collections:
            self._collections[collection_name] = []
        self._collections[collection_name].extend(points)
    
    def search(self, collection_name: str, query_vector: List[float], limit: int, query_filter=None):
        # Return empty results for mock
        return []
    
    def delete(self, collection_name: str, points_selector: List[str]):
        if collection_name in self._collections:
            ids_to_keep = set(points_selector)
            self._collections[collection_name] = [
                p for p in self._collections[collection_name]
                if p.id not in ids_to_keep
            ]
    
    def count(self, collection_name: str, query_filter=None):
        class Count:
            def __init__(self, count):
                self.count = count
        return Count(len(self._collections.get(collection_name, [])))
