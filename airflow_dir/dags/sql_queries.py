emailTable_create = ("""
    CREATE TABLE IF NOT EXISTS emails(
    id integer PRIMARY KEY,
    body text,
    header text,
    sender text,
    date text);
    """)

emailTable_drop = "DROP TABLE if exists emails"

emailTable_insert = ("""INSERT INTO emails(
id,
body,
header,
sender,
date)
VALUES (%s,%s,%s,%s,%s)
ON CONFLICT DO NOTHING
""")

