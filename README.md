# DuckDB FastAPI

DuckDB FastAPI is a Python package that integrates DuckDB with RESTFul APIs via FastAPI.

## Use-cases

- **Instant API Creation from DuckDB macros**: Automatically generates REST endpoints for all your DuckDB macros, inspited by PostgREST.
- **Serve your API endpoints directly from DuckDB**: Automatically generate a REST endpoint that enables API consumers to query your API endpoints inside DuckDB via `ATTACH 'https://your-api.com/.duckdb' AS myapi;`

## Installation

You can install the package using `uv`:

```bash
uv pip install duckdb-fastapi
```

Or using pip:

```bash
pip install duckdb-fastapi
```

## Create FastAPI from DuckDB 

Here's how to create an API from your DuckDB macros:

```python
import duckdb
from duckdb_fastapi import DuckDBFastAPI
import uvicorn

conn = duckdb.connect()
conn.execute("CREATE MACRO get_sample() AS TABLE SELECT 1 as t")
conn.execute("CREATE MACRO sample_rows(rowcount) AS TABLE SELECT unnest(generate_series(1, rowcount)) as idx")

# Create a FastAPI app from your DuckDB connection
db_fastapi = DuckDBFastAPI(conn)
app = db_fastapi.create_app()

# Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

DuckDB FastAPI will automatically create these endpoints:

- `curl "http://localhost:8000/macro/get_sample"`
```
[{"t": 1}]
```

- `curl "http://localhost:8000/sample_rows?rowcount=10"`

```
[{"idx": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}]
```

## Create DuckDB from FastAPI

You can also convert your FastAPI endpoints into DuckDB macros, allowing you to query your API endpoints directly from DuckDB using the HTTP client extension:

```python
from fastapi import FastAPI
from duckdb_fastapi import create_duckdb_endpoint

app = FastAPI()

@app.get("/items/{item_id}", operation_id="get_item")
def read_item(item_id: str):
    return {"item_id": item_id}

# Add the DuckDB endpoint
create_duckdb_endpoint(app)
```

Now you can query your API directly from DuckDB:

```sql
-- Install HTTP client extension
INSTALL httpfs;
LOAD httpfs;

-- Attach your API as a database
ATTACH 'http://localhost:8000/.duckdb' AS myapi;

-- Query your API endpoints as tables
SELECT * FROM myapi.get_item('123');
```

## Development Setup

1. Clone the repository
2. Install development dependencies:

```bash
uv pip install -e ".[dev]"
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
