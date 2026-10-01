"""Format query results for display or CSV output."""
import csv
from io import StringIO

def rows_to_csv(rows):
    if not rows:
        return ''
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()
