import duckdb

conn = duckdb.connect(r"data\gym.duckdb")

print("📊 estructuras:")
print(conn.execute("""
    SELECT 
        url_ejercicio
    FROM bronze_series
""").fetchdf())

conn.close()