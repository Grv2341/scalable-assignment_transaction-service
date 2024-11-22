import sqlite3
import uuid
from datetime import datetime

DB_PATH = "transaction_service.db"

def initialize_db():

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Create transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            sender_id TEXT,
            receiver_id TEXT,
            amount REAL,
            status TEXT,
            transaction_type TEXT,
            transaction_date TEXT
        )
    ''')
    connection.commit()
    connection.close()


def record_transaction(sender_id, receiver_id, amount, status, transaction_type):

    transaction_id = str(uuid.uuid4())
    transaction_date = datetime.now().isoformat()

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute('''
        INSERT INTO transactions (transaction_id, sender_id, receiver_id, amount, status, transaction_type, transaction_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (transaction_id, sender_id, receiver_id, amount, status, transaction_type, transaction_date))

    connection.commit()
    connection.close()

    return transaction_id

def get_transaction_status_db(transaction_id):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute('''
        SELECT transaction_id, sender_id, receiver_id, amount, status, transaction_type, transaction_date
        FROM transactions
        WHERE transaction_id = ?
    ''', (transaction_id,))
    transaction = cursor.fetchone()

    connection.close()

    if transaction:
        # Map database fields to a dictionary
        transaction_data = {
            "transaction_id": transaction[0],
            "sender_id": transaction[1],
            "amount": transaction[3],
            "status": transaction[4],
            "transaction_type": transaction[5],
            "transaction_date": transaction[6],
        }
        # Only include receiver_id if it is not None
        if transaction[2] is not None:
            transaction_data["receiver_id"] = transaction[2]

        return transaction_data

    return None
