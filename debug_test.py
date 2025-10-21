#!/usr/bin/env python3
"""Debug test to isolate the 404 issue."""

import pytest
from fastapi.testclient import TestClient
from api.main import app

def test_simple_upload():
    """Simple test to debug upload endpoint."""
    client = TestClient(app)
    
    # Test without authentication - should get 401
    response = client.post("/api/transactions/upload")
    print(f"POST /api/transactions/upload (no auth): {response.status_code}")
    print(f"Response: {response.text[:100]}...")
    
    # Test with mock auth header - should get 401 (invalid token)
    headers = {"Authorization": "Bearer mock-token"}
    response = client.post("/api/transactions/upload", headers=headers)
    print(f"POST /api/transactions/upload (mock auth): {response.status_code}")
    print(f"Response: {response.text[:100]}...")
    
    # Test with proper mock auth from conftest
    from tests.conftest import mock_firebase_token
    token = mock_firebase_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/transactions/upload", headers=headers)
    print(f"POST /api/transactions/upload (conftest auth): {response.status_code}")
    print(f"Response: {response.text[:100]}...")

if __name__ == "__main__":
    test_simple_upload()

