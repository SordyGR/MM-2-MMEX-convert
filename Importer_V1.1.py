# Made with ChatGPT, DeepSeek, half a pouch of tobacco and 3 litres of cheap cola.
# This code assumes my locale settings. .CSV files are seperated by semicolons ";" instead of comas
# !!!!!!!!!! BACKUP BEFORE USE !!!!!!!!!!!!
# Date values have to be in YYYY-MM-DDTHH:mm:ss Format
import sqlite3
import csv
import logging
from datetime import datetime
from tkinter import Tk, filedialog

# Configure logging
logging.basicConfig(level=logging.INFO)

def get_database_connection(db_path):
    """Connect to the MMEX .mmb SQLite database."""
    return sqlite3.connect(db_path)

def get_or_create_id(cursor, table, name_column, id_column, name_value):
    """Get the ID of a record by name, or create it if it doesn't exist."""
    cursor.execute(f"SELECT {id_column} FROM {table} WHERE {name_column} = ?", (name_value,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    else:
        cursor.execute(f"INSERT INTO {table} ({name_column}) VALUES (?)", (name_value,))
        return cursor.lastrowid

def get_or_create_category_id(cursor, category_name, subcategory_name=None):
    """
    Handle categories and subcategories.
    If subcategory_name is provided, it treats it as a subcategory of category_name.
    """
    # Get or create the parent category
    cursor.execute("SELECT CATEGID FROM CATEGORY_V1 WHERE CATEGNAME = ? AND PARENTID = -1", (category_name,))
    parent_category = cursor.fetchone()
    
    if not parent_category:
        # Create the parent category if it doesn't exist
        cursor.execute("INSERT INTO CATEGORY_V1 (CATEGNAME, PARENTID) VALUES (?, -1)", (category_name,))
        parent_id = cursor.lastrowid
    else:
        parent_id = parent_category[0]
    
    if subcategory_name:
        # Get or create the subcategory
        cursor.execute("SELECT CATEGID FROM CATEGORY_V1 WHERE CATEGNAME = ? AND PARENTID = ?", (subcategory_name, parent_id))
        subcategory = cursor.fetchone()
        
        if not subcategory:
            # Create the subcategory if it doesn't exist
            cursor.execute("INSERT INTO CATEGORY_V1 (CATEGNAME, PARENTID) VALUES (?, ?)", (subcategory_name, parent_id))
            return cursor.lastrowid
        else:
            return subcategory[0]
    else:
        # Return the parent category ID if no subcategory is provided
        return parent_id

def import_csv_to_mmex(db_path, csv_path):
    """Import transactions from a CSV file into the MMEX database."""
    conn = get_database_connection(db_path)
    cursor = conn.cursor()
    
    with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:  # Use 'utf-8-sig' to handle BOM
        reader = csv.DictReader(csvfile, delimiter=';')  # Use semicolon as the delimiter
        
        # Print headers for debugging
        logging.info(f"CSV Headers: {reader.fieldnames}")
        
        # Strip BOM from headers if present, remove 'ca', and remove empty columns
        reader.fieldnames = [field.strip('\ufeff') for field in reader.fieldnames if field.strip() and field.strip('\ufeff') != 'ca']
        logging.info(f"Cleaned Headers: {reader.fieldnames}")
        
        # Map incorrect headers to correct ones
        header_map = {
            'ca': 'TRANSDATE',  # Map 'ca' to 'TRANSDATE'
        }
        reader.fieldnames = [header_map.get(field, field) for field in reader.fieldnames]
        logging.info(f"Mapped Headers: {reader.fieldnames}")
        
        # Required fields (adjust as needed)
        required_fields = ['TRANSDATE', 'ACCOUNT', 'PAYEE', 'CATEGORY', 'TRANSCODE', 'TRANSAMOUNT']
        optional_fields = ['SUBCATEGORY', 'NOTES']
        batch_size = 100
        
        for i, row in enumerate(reader):
            # Print the first few rows for debugging
            if i < 5:
                logging.debug(f"Row {i + 1}: {row}")
            
            # Validate required fields
            if not all(field in row and row[field] for field in required_fields):
                logging.warning(f"Skipping row {i + 1}: Missing or empty required fields.")
                continue
            
            try:
                # Use the TRANSDATE value directly (no need to parse/reformat)
                trans_date = row['TRANSDATE']
                
                # Get or create account ID
                account_id = get_or_create_id(cursor, 'ACCOUNTLIST_V1', 'ACCOUNTNAME', 'ACCOUNTID', row['ACCOUNT'])
                
                # Get or create payee ID
                payee_id = get_or_create_id(cursor, 'PAYEE_V1', 'PAYEENAME', 'PAYEEID', row['PAYEE'])
                
                # Get or create category ID (handles subcategories)
                subcategory = row.get('SUBCATEGORY', '').strip()  # Handle empty subcategory
                category_id = get_or_create_category_id(cursor, row['CATEGORY'], subcategory if subcategory else None)
                
                # Insert the transaction
                cursor.execute(
                    """
                    INSERT INTO CHECKINGACCOUNT_V1 (TRANSDATE, ACCOUNTID, PAYEEID, TRANSCODE, TRANSAMOUNT, NOTES, CATEGID)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (trans_date, account_id, payee_id, row['TRANSCODE'], row['TRANSAMOUNT'], row.get('NOTES', ''), category_id)
                )
                
                # Commit in batches
                if i % batch_size == 0:
                    conn.commit()
            except sqlite3.IntegrityError as e:
                logging.error(f"Error inserting row {i + 1}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error in row {i + 1}: {e}")
        
        conn.commit()
    conn.close()
    logging.info("CSV data imported successfully.")

if __name__ == "__main__":
    Tk().withdraw()
    db_path = filedialog.askopenfilename(title="Select Money Manager EX Database (.mmb)", filetypes=[("MMEX DB", "*.mmb")])
    csv_path = filedialog.askopenfilename(title="Select CSV File", filetypes=[("CSV Files", "*.csv")])
    
    if db_path and csv_path:
        import_csv_to_mmex(db_path, csv_path)
    else:
        logging.warning("Operation canceled.")