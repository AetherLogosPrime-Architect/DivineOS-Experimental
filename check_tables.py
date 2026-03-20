from divineos.core.ledger import init_db, _get_connection
init_db()
conn = _get_connection()
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables in database:')
for table in tables:
    print(f'  - {table[0]}')
conn.close()
