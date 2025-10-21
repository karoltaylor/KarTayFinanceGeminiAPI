#!/usr/bin/env python3
"""Simple debug test to isolate the issue."""

import pytest
from fastapi.testclient import TestClient
from api.main import app

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

@pytest.fixture
def auth_headers():
    """Get authentication headers."""
    return {"Authorization": "Bearer test-token"}

def test_upload_endpoint_exists(client, auth_headers):
    """Test that upload endpoint exists and responds."""
    # Test without authentication - should get 401
    response = client.post("/api/transactions/upload")
    print(f"POST /api/transactions/upload (no auth): {response.status_code}")
    print(f"Response: {response.text[:100]}...")
    
    # Test with auth header - should get 401 (invalid token)
    response = client.post("/api/transactions/upload", headers=auth_headers)
    print(f"POST /api/transactions/upload (with auth): {response.status_code}")
    print(f"Response: {response.text[:100]}...")
    
    # Both should return 401, not 404
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"

if __name__ == "__main__":
    # Run the test manually
    import sys
    sys.path.append('.')
    
    client_fixture = TestClient(app)
    auth_headers_fixture = {"Authorization": "Bearer test-token"}
    
    test_upload_endpoint_exists(client_fixture, auth_headers_fixture)

