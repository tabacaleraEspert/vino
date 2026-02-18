from app.sheets.service import read_table

headers, rows = read_table("movimientos")
print("headers:", headers[:10])
print("rows:", len(rows))
print("first:", rows[0] if rows else None)
