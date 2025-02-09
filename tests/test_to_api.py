"""Tests for DuckDB to FastAPI conversion."""
import pytest
import duckdb
from fastapi.testclient import TestClient
from duckdb_fastapi import DuckDBFastAPI

@pytest.fixture
def duckdb_conn():
    """Create a DuckDB connection with test macros."""
    conn = duckdb.connect(':memory:')
    conn.execute("CREATE MACRO get_sample() AS TABLE SELECT 1 as t")
    conn.execute("CREATE MACRO sample_rows(rowcount INTEGER) AS TABLE SELECT unnest(generate_series(1, rowcount)) as idx")
    return conn

@pytest.fixture
def api_client(duckdb_conn):
    """Create a test client for the FastAPI app."""
    db_fastapi = DuckDBFastAPI(duckdb_conn)
    app = db_fastapi.create_app()
    return TestClient(app)

def test_get_sample_endpoint(api_client):
    """Test endpoint for macro without parameters."""
    response = api_client.get("/macro/get_sample")
    assert response.status_code == 200
    assert response.json() == {"result": [[1]]}

def test_sample_rows_endpoint(api_client):
    """Test endpoint for macro with parameters."""
    response = api_client.get("/macro/sample_rows?rowcount=3")
    assert response.status_code == 200
    assert response.json() == {"result": [[1], [2], [3]]}

def test_invalid_parameter(api_client):
    """Test endpoint with invalid parameter type."""
    response = api_client.get("/macro/sample_rows?rowcount=invalid")
    assert response.status_code == 422  # Validation error

def test_nonexistent_macro(api_client):
    """Test calling a macro that doesn't exist."""
    response = api_client.get("/macro/nonexistent")
    assert response.status_code == 404

def test_macro_execution_error(duckdb_conn, api_client):
    """Test error handling when macro execution fails."""
    # Create a macro that will fail
    duckdb_conn.execute("CREATE MACRO failing_macro() AS TABLE SELECT * FROM nonexistent_table")
    response = api_client.get("/macro/failing_macro")
    assert response.status_code == 500
    assert "Error executing macro" in response.json()["detail"]
