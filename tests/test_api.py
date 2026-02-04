"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


class TestHealthCheck:
    """Tests for health check endpoint."""
    
    def test_health_check(self):
        """Test health check endpoint."""
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestDocumentUpload:
    """Tests for document upload endpoint."""
    
    def test_upload_no_file(self):
        """Test upload without file."""
        client = TestClient(app)
        response = client.post("/api/documents/upload")
        assert response.status_code == 422  # Validation error
    
    def test_upload_invalid_file_type(self):
        """Test upload with invalid file type."""
        client = TestClient(app)
        from io import BytesIO
        
        files = {"file": ("test.exe", BytesIO(b"fake content"), "application/x-msdownload")}
        response = client.post("/api/documents/upload", files=files)
        assert response.status_code == 415  # Unsupported media type
    
    def test_upload_large_file(self):
        """Test upload with file exceeding size limit."""
        client = TestClient(app)
        from io import BytesIO
        
        # Create a file larger than max size (10MB)
        large_content = b"x" * (11 * 1024 * 1024)
        files = {"file": ("large.txt", BytesIO(large_content), "text/plain")}
        response = client.post("/api/documents/upload", files=files)
        assert response.status_code == 413  # Payload too large


class TestQuery:
    """Tests for query endpoint."""
    
    def test_query_empty(self):
        """Test query with empty question."""
        client = TestClient(app)
        response = client.post("/api/query", json={"question": ""})
        assert response.status_code == 400  # Bad request
    
    def test_query_too_long(self):
        """Test query with question exceeding max length."""
        client = TestClient(app)
        long_question = "x" * 1001
        response = client.post("/api/query", json={"question": long_question})
        assert response.status_code == 400  # Bad request
    
    def test_query_invalid_top_k(self):
        """Test query with invalid top_k value."""
        client = TestClient(app)
        response = client.post("/api/query", json={"question": "test", "top_k": 100})
        assert response.status_code == 400  # Bad request


class TestRateLimiting:
    """Tests for rate limiting."""
    
    def test_health_check_rate_limit(self):
        """Test that health check has rate limiting."""
        client = TestClient(app)
        # Make many requests to hit rate limit
        for _ in range(105):  # Above 100/minute limit
            response = client.get("/api/health")
        
        # Should be rate limited
        response = client.get("/api/health")
        assert response.status_code == 429  # Too many requests


class TestSecurityHeaders:
    """Tests for security headers."""
    
    def test_cors_headers(self):
        """Test CORS headers are present."""
        client = TestClient(app)
        response = client.get("/api/health")
        assert "access-control-allow-origin" in response.headers


class TestInputValidation:
    """Tests for input validation."""
    
    def test_document_id_validation(self):
        """Test document ID validation."""
        client = TestClient(app)
        response = client.delete("/api/documents/short")
        assert response.status_code == 400  # Invalid ID format
