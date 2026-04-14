import sqlite3

conn = sqlite3.connect('interview_prep.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print("\n" + "="*60)
print("EXISTING TABLES IN DATABASE")
print("="*60)

for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]
    print(f"\n[{table_name}] - {row_count} rows")
    
    # Show columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for col in columns:
        col_id, col_name, col_type, not_null, default, pk = col
        print(f"    {col_name}: {col_type}")

conn.close()
print("\n" + "="*60)
