"""
Test for health check endpoint
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

import sys
import os

# Add repository root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.app.main import app


client = TestClient(app)


def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/health/")
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert data["version"] == "1.0.0"
    
    # Verify timestamp is valid ISO format
    timestamp_str = data["timestamp"]
    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    assert isinstance(timestamp, datetime)


def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == "Cyborgs Protected Chat System"
    assert data["version"] == "1.0.0"
    assert data["status"] == "running"
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"


def test_docs_endpoint():
    """Test that the docs endpoint is accessible"""
    response = client.get("/docs")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_redoc_endpoint():
    """Test that the redoc endpoint is accessible"""
    response = client.get("/redoc")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
