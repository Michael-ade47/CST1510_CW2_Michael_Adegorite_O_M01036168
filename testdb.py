import sqlite3

dbcon = sqlite3.connect('university.db')
cur = dbcon.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS student(
    MISIS TEXT PRIMARY KEY, stdname TEXT, programme TEXT, mark INTEGER)''')

cur.execute("INSERT INTO student(MISIS, stdname, programme, mark) VALUES (?, ?, ?, ?)", 
            ('M0101', 'Ali', 'IT', 70))
dbcon.commit()
cur.execute("SELECT * FROM student")
print(cur.fetchall())
dbcon.close()


