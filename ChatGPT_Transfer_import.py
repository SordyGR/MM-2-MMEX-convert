import sqlite3
import csv
import logging
from logging.handlers import RotatingFileHandler
from tkinter import Tk, filedialog

# ---------------- LOGGING ----------------
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    file_handler = RotatingFileHandler(
        "mmex_transfer_import.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

setup_logging()

# ---------------- DB HELPERS ----------------
def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.text_factory = str
    return conn

def get_or_create_account_id(cursor, account_name):
    cursor.execute(
        "SELECT ACCOUNTID FROM ACCOUNTLIST_V1 WHERE ACCOUNTNAME = ?",
        (account_name.strip(),)
    )
    row = cursor.fetchone()

    if row:
        return row[0]

    cursor.execute(
        """
        INSERT INTO ACCOUNTLIST_V1 (ACCOUNTNAME, ACCOUNTTYPE)
        VALUES (?, 'Checking')
        """,
        (account_name.strip(),)
    )

    logging.info(f"Created account: {account_name}")
    return cursor.lastrowid

# ---------------- IMPORT LOGIC ----------------
def import_transfers(db_path, csv_path):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")

        logging.info(f"CSV headers: {reader.fieldnames}")

        required = {"TRANSDATE", "FROM_ACCOUNT", "TO_ACCOUNT", "TRANSAMOUNT"}

        for i, row in enumerate(reader, start=1):
            if not required.issubset(row) or not all(row[k] for k in required):
                logging.warning(f"Row {i} skipped: missing required fields")
                continue

            try:
                trans_date = row["TRANSDATE"]           # used as-is
                from_name = row["FROM_ACCOUNT"].strip()
                to_name = row["TO_ACCOUNT"].strip()
                amount = abs(float(row["TRANSAMOUNT"]))
                notes = row.get("NOTES", "").strip()

                from_id = get_or_create_account_id(cursor, from_name)
                to_id = get_or_create_account_id(cursor, to_name)

                if from_id == to_id:
                    logging.warning(f"Row {i} skipped: same source/destination")
                    continue

                # MMEX V2 Transfer INSERT
                cursor.execute(
                    """
                    INSERT INTO CHECKINGACCOUNT_V1
                    (
                        TRANSDATE,
                        ACCOUNTID,
                        TOACCOUNTID,
                        PAYEEID,
                        TRANSCODE,
                        TRANSAMOUNT,
                        TOTRANSAMOUNT,
                        NOTES,
                        CATEGID
                    )
                    VALUES (?, ?, ?, -1, 'Transfer', ?, ?, ?, -1)
                    """,
                    (
                        trans_date,
                        from_id,
                        to_id,
                        amount,   # withdrawal
                        amount,   # deposit
                        notes
                    )
                )

                if i % 100 == 0:
                    conn.commit()
                    logging.info(f"Committed {i} rows")

            except ValueError as e:
                logging.error(f"Row {i} amount error: {e}")
            except sqlite3.Error as e:
                logging.error(f"Row {i} DB error: {e}")

    conn.commit()
    conn.close()
    logging.info("Transfer import completed successfully")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    Tk().withdraw()

    db_path = filedialog.askopenfilename(
        title="Select MMEX database",
        filetypes=[("Money Manager EX DB", "*.mmb")]
    )

    csv_path = filedialog.askopenfilename(
        title="Select transfer CSV",
        filetypes=[("CSV files", "*.csv")]
    )

    if not db_path or not csv_path:
        logging.warning("Operation cancelled")
    else:
        logging.info("Starting MMEX transfer import")
        logging.info(f"DB: {db_path}")
        logging.info(f"CSV: {csv_path}")
        import_transfers(db_path, csv_path)
