def count_rows(rows):
    tmp = 0
    for row in rows:
        if row.strip():
            tmp += 1
    return tmp
