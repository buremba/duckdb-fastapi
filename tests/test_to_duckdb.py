"""Tests for FastAPI to DuckDB conversion."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from duckdb_fastapi import create_duckdb_endpoint

@pytest.fixture
def sample_app():
    """Create a sample FastAPI app with test endpoints."""
    app = FastAPI()
    
    @app.get("/items/{item_id}", operation_id="get_item")
    def read_item(item_id: str):
        return {"item_id": item_id}
    
    @app.get("/search", operation_id="search_items")
    def search_items(q: str = None, limit: int = 10):
        return {"query": q, "limit": limit}
    
    create_duckdb_endpoint(app)
    return app

@pytest.fixture
def test_client(sample_app):
    """Create a test client for the FastAPI app."""
    return TestClient(sample_app)

def test_duckdb_endpoint_exists(test_client):
    """Test that the .duckdb endpoint is created."""
    response = test_client.get("/.duckdb")
    assert response.status_code == 200
    assert "CREATE OR REPLACE MACRO" in response.text

def test_path_parameter_macro(test_client):
    """Test that path parameters are correctly converted to macro parameters."""
    response = test_client.get("/.duckdb")
    sql = response.text
    assert "get_item(item_id VARCHAR)" in sql
    assert "http_get_table(" in sql
    assert "'http://localhost:8000/items/' || item_id" in sql

def test_query_parameter_macro(test_client):
    """Test that query parameters are correctly converted to macro parameters."""
    response = test_client.get("/.duckdb")
    sql = response.text
    assert "search_items(q VARCHAR, limit VARCHAR)" in sql
    assert "http_get_table(" in sql
    assert "'http://localhost:8000/search'" in sql

def test_generated_sql_is_valid():
    """Test that the generated SQL can be executed in DuckDB."""
    import duckdb
    
    app = FastAPI()
    
    @app.get("/test/{id}", operation_id="test_macro")
    def test_endpoint(id: str):
        return {"id": id}
    
    create_duckdb_endpoint(app)
    
    with TestClient(app) as client:
        sql = client.get("/.duckdb").text
        
    # This should not raise any syntax errors
    conn = duckdb.connect(':memory:')
    conn.execute("INSTALL httpfs")
    conn.execute("LOAD httpfs")
    conn.execute(sql)
