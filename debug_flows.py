import duckdb
import hashlib

# Mock location logic from app.py
cities = [
    {"city": "Prayagraj", "country": "India", "lat": 25.4358, "lon": 81.8463},
    {"city": "Delhi", "country": "India", "lat": 28.6139, "lon": 77.2090},
    {"city": "Mumbai", "country": "India", "lat": 19.0760, "lon": 72.8777},
    {"city": "Bangalore", "country": "India", "lat": 12.9716, "lon": 77.5946},
    {"city": "Chennai", "country": "India", "lat": 13.0827, "lon": 80.2707},
    {"city": "Kolkata", "country": "India", "lat": 22.5726, "lon": 88.3639},
    {"city": "Hyderabad", "country": "India", "lat": 17.3850, "lon": 78.4867},
    {"city": "Pune", "country": "India", "lat": 18.5204, "lon": 73.8567},
    {"city": "Jaipur", "country": "India", "lat": 26.9124, "lon": 75.7873},
    {"city": "Lucknow", "country": "India", "lat": 26.8467, "lon": 80.9462},
    {"city": "Singapore", "country": "Singapore", "lat": 1.3521, "lon": 103.8198},
    {"city": "Dubai", "country": "UAE", "lat": 25.2048, "lon": 55.2708},
    {"city": "London", "country": "UK", "lat": 51.5074, "lon": -0.1278},
    {"city": "New York", "country": "USA", "lat": 40.7128, "lon": -74.0060},
    {"city": "Tokyo", "country": "Japan", "lat": 35.6762, "lon": 139.6503},
    {"city": "Sydney", "country": "Australia", "lat": -33.8688, "lon": 151.2093},
]


def get_city(ip):
    if not ip:
        return "None"
    ip_hash = int(hashlib.md5(ip.encode()).hexdigest()[:8], 16)
    return cities[ip_hash % len(cities)]["city"]


conn = duckdb.connect()
conn.execute(
    "CREATE TABLE packets AS SELECT * FROM read_parquet('data/parquet/global_test.parquet')"
)

print("Top 10 Flows:")
print("-" * 60)
results = conn.execute(
    """
    SELECT "src_ip", "dst_ip", COUNT(*) as count 
    FROM packets 
    WHERE "src_ip" IS NOT NULL AND "dst_ip" IS NOT NULL
    GROUP BY 1, 2 
    ORDER BY 3 DESC 
    LIMIT 10
"""
).fetchall()

for src, dst, count in results:
    src_city = get_city(src)
    dst_city = get_city(dst)
    print(f"{src} ({src_city}) -> {dst} ({dst_city}) : {count} packets")
