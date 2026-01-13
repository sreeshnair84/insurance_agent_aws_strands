"""
Script to normalize existing ClaimType values in the SQLite database.
Converts lowercase/mixed-case values (e.g., 'Health') to uppercase ('HEALTH').
"""
import os
import sqlite3

def fix_database():
    db_path = "backend/sql_app.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}.")
        return

    print(f"[*] Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Uppercase all claim_type values
    print("[*] Normalizing claim_type values...")
    cursor.execute("UPDATE claims SET claim_type = UPPER(claim_type)")
    
    # Uppercase all status values just in case
    print("[*] Normalizing status values...")
    cursor.execute("UPDATE claims SET status = UPPER(status)")
    
    conn.commit()
    print(f"[OK] Rows updated: {conn.total_changes}")
    conn.close()

if __name__ == "__main__":
    fix_database()
