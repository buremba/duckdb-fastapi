"""DuckDB FastAPI application generator."""
from typing import Any, Dict, List, Optional, Union

import duckdb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, create_model


class DuckDBFastAPI:
    """Creates a FastAPI application from DuckDB macros."""

    def __init__(self, connection: duckdb.DuckDBPyConnection):
        """Initialize the DuckDB FastAPI generator.
        
        Args:
            connection: A DuckDB connection instance created via duckdb.connect()
        """
        self.conn = connection
        
    def _get_macro_info(self) -> List[Dict[str, Any]]:
        """Get information about all macros in the database."""
        macro_query = """
        SELECT 
            macro_name,
            parameters,
            return_type,
            macro_definition
        FROM duckdb_macros()
        """
        try:
            return self.conn.execute(macro_query).fetchall()
        except Exception as e:
            raise ValueError(f"Failed to fetch macros: {str(e)}")

    def _create_endpoint_model(self, parameters: str) -> BaseModel:
        """Create a Pydantic model for the endpoint parameters."""
        # Parse parameters string into field definitions
        param_list = [p.strip().split(' ') for p in parameters.split(',') if p.strip()]
        fields = {}
        
        for param in param_list:
            if len(param) >= 2:
                param_name = param[1].strip()
                param_type = param[0].lower()
                
                # Map DuckDB types to Python types
                python_type: Any = str  # default
                if param_type in ('integer', 'bigint'):
                    python_type = int
                elif param_type in ('double', 'float'):
                    python_type = float
                elif param_type in ('boolean'):
                    python_type = bool
                
                fields[param_name] = (python_type, ...)

        return create_model('MacroParams', **fields)

    def create_app(self) -> FastAPI:
        """Create a FastAPI application with endpoints for each macro.
        
        Returns:
            FastAPI: The configured FastAPI application
        """
        app = FastAPI(
            title="DuckDB Macro API",
            description="Automatically generated API endpoints for DuckDB macros",
            version="1.0.0"
        )

        macros = self._get_macro_info()

        for macro_name, parameters, return_type, macro_def in macros:
            # Create parameter model if the macro has parameters
            if parameters:
                param_model = self._create_endpoint_model(parameters)
            else:
                param_model = None

            # Create the endpoint handler
            async def create_handler(
                macro_name=macro_name,
                param_model=param_model
            ):
                async def handler(params: Optional[param_model] = None):
                    try:
                        if params:
                            # Execute macro with parameters
                            param_dict = params.dict()
                            param_str = ", ".join(str(v) for v in param_dict.values())
                            query = f"SELECT {macro_name}({param_str})"
                        else:
                            # Execute macro without parameters
                            query = f"SELECT {macro_name}()"
                            
                        result = self.conn.execute(query).fetchall()
                        return {"result": result}
                    except Exception as e:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Error executing macro: {str(e)}"
                        )
                return handler

            # Register the endpoint
            endpoint = create_handler()
            
            if param_model:
                app.post(
                    f"/macro/{macro_name}",
                    response_model=Dict[str, Any],
                    summary=f"Execute {macro_name} macro",
                    description=f"Execute the {macro_name} macro with the given parameters"
                )(endpoint)
            else:
                app.get(
                    f"/macro/{macro_name}",
                    response_model=Dict[str, Any],
                    summary=f"Execute {macro_name} macro",
                    description=f"Execute the {macro_name} macro"
                )(endpoint)

        return app
