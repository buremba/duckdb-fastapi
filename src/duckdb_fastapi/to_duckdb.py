"""Convert FastAPI endpoints to DuckDB macros using HTTP client extension."""

from typing import Any, Dict, List, Optional
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.openapi.utils import get_openapi


def create_duckdb_macros(app: FastAPI) -> str:
    """Create DuckDB macros from FastAPI OpenAPI schema.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        SQL script that creates DuckDB macros for each endpoint
    """
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes
    )
    
    macros = []
    
    for path, path_item in openapi_schema['paths'].items():
        for method, operation in path_item.items():
            if not operation.get('operationId'):
                continue
                
            operation_id = operation['operationId']
            parameters = operation.get('parameters', [])
            
            # Convert path parameters to macro parameters
            param_names = []
            param_declarations = []
            
            # Handle path parameters
            for param in parameters:
                if param['in'] == 'path':
                    param_name = param['name']
                    param_names.append(param_name)
                    param_declarations.append(f"{param_name} VARCHAR")
                    
            # Handle query parameters
            for param in parameters:
                if param['in'] == 'query':
                    param_name = param['name']
                    param_names.append(param_name)
                    param_declarations.append(f"{param_name} VARCHAR")
            
            # Create the macro
            param_list = ', '.join(param_declarations)
            param_values = ', '.join(f"'{{{p}}}'" for p in param_names)
            
            # Replace path parameters in URL
            url = path
            for param in param_names:
                url = url.replace(f"{{{param}}}", f"' || {param} || '")
            
            macro = f"""
            CREATE OR REPLACE MACRO {operation_id}({param_list if param_list else ''}) AS
            SELECT * 
            FROM http_get_table(
                'http://localhost:8000{url}',
                {{'method': '{method.upper()}'}}::JSON
            );
            """.strip()
            
            macros.append(macro)
    
    return '\n\n'.join(macros)


def create_duckdb_endpoint(app: FastAPI):
    """Create an endpoint that serves DuckDB macros.
    
    Args:
        app: FastAPI application instance
    """
    sql_script = create_duckdb_macros(app)
    
    @app.get("/.duckdb", include_in_schema=False)
    async def get_duckdb_macros():
        return sql_script