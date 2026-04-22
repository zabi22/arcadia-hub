import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("ALTER TABLE achievements ADD COLUMN achievement_key TEXT")

conn.commit()
conn.close()

print("Fixed!")