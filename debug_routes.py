#!/usr/bin/env python3
"""Debug script to test route accessibility."""

from fastapi.testclient import TestClient
from api.main import app
import json


def test_routes():
    """Test all routes to see which ones work."""
    client = TestClient(app)

    # Test basic routes
    print("=== Testing Basic Routes ===")
    response = client.get("/")
    print(f"GET /: {response.status_code}")

    response = client.get("/health")
    print(f"GET /health: {response.status_code}")

    # Test wallet routes
    print("\n=== Testing Wallet Routes ===")
    response = client.get("/api/wallets")
    print(f"GET /api/wallets: {response.status_code}")

    # Test transaction routes
    print("\n=== Testing Transaction Routes ===")
    response = client.get("/api/transactions")
    print(f"GET /api/transactions: {response.status_code}")
    print(f"Response: {response.text[:100]}...")

    response = client.post("/api/transactions/upload")
    print(f"POST /api/transactions/upload (no data): {response.status_code}")
    print(f"Response: {response.text[:100]}...")

    # Test with auth header
    print("\n=== Testing with Auth Header ===")
    headers = {"Authorization": "Bearer test-token"}
    response = client.get("/api/transactions", headers=headers)
    print(f"GET /api/transactions (with auth): {response.status_code}")
    print(f"Response: {response.text[:100]}...")

    response = client.post("/api/transactions/upload", headers=headers)
    print(f"POST /api/transactions/upload (with auth, no data): {response.status_code}")
    print(f"Response: {response.text[:100]}...")


if __name__ == "__main__":
    test_routes()
