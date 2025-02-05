import sqlite3 as sql 

conn = sql.connect('UI/src/database/users.db')

cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS Users (
username text, 
password text
)''')

addCommand = '''INSERT INTO Users VALUES {}'''
data = ('admin', 'user123')

cursor.execute(addCommand.format(data))

for row in cursor.execute('SELECT * FROM Users'):
    print(row)

conn.commit()
conn.close()