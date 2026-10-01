"""duckdb_loader.py - connect and optionally register parquet as a table."""
import duckdb

def connect(parquet_path: str = None):
    con = duckdb.connect(database=':memory:')
    if parquet_path:
        con.execute(f"CREATE TABLE packets AS SELECT * FROM read_parquet('{parquet_path}')")
    return con
