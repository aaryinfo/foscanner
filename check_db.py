import sqlite3
conn = sqlite3.connect('auth.db')
c = conn.cursor()
c.execute("SELECT * FROM users")
for row in c.fetchall():
    print(row)
conn.close()
