# 01 – Inventory CLI (Python + SQLite)

A small command-line program for recording stock items in a local SQLite database.

**What it does today**
- Add an item (name, quantity, location; timestamped)
- List all items

**Run**
```bash
cd 01-inventory-system
python Main.py
```
The database file `inventory.db` is created on first run.

**Built with:** Python 3, `sqlite3` (standard library), parameterized SQL queries (prevents SQL injection).

**Possible next steps:** edit/delete items, low-stock report, input validation for non-numeric quantities, unit tests with an in-memory database.
