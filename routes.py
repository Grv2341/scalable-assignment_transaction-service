from flask import Blueprint, request, jsonify
import requests
import jwt
from db import record_transaction, get_transaction_status_db
import os
from auth import generate_jwt
from kafka import KafkaProducer
import json

routes = Blueprint("routes", __name__)

WALLET_SERVICE_BASE_URL = os.getenv("BASE_URL")
JWT_SECRET = os.getenv("SECRET_PHRASE")

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
)

@routes.route("/transaction", methods=["POST"])
def initiate_transaction():

    data = request.get_json()

    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        print(decoded_token)
        sender_id = decoded_token.get("user_id")
    except jwt.ExpiredSignatureError:
        return jsonify({"status": "error","message": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"status": "error", "message": "Invalid or missing token"}), 401

    required_fields = ["amount"]
    if "transaction_type" not in data:
        return jsonify({"status": "error", "message": "Missing field: transaction_type"}), 400
    if data["transaction_type"] == "MONEY_TRANSFER":
        required_fields.append("receiver_id")

    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"status": "error", "message": f"Missing fields: {', '.join(missing_fields)}"}), 400

    receiver_id = data.get("receiver_id")
    amount = data["amount"]
    transaction_type = data["transaction_type"]

    if receiver_id == sender_id:
        return jsonify({"status": "error", "message": "You cannot transfer money to yourself"}), 400

    internalToken = generate_jwt(sender_id)
    if not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({"status": "error", "message": "Amount must be a positive number"}), 400

    if transaction_type not in ["MONEY_TRANSFER", "WALLET_RECHARGE"]:
        return jsonify({"status": "error", "message": "Invalid transaction_type"}), 400

    if transaction_type == "MONEY_TRANSFER":
        sender_response = requests.post(
            f"{WALLET_SERVICE_BASE_URL}/transaction",
            json={"user_id": sender_id, "transaction_type": "DEBIT", "amount": amount},
            headers={"Authorization": f"Bearer {internalToken}"},
        )
        print(sender_response.json())
        if sender_response.status_code != 200:
            record_transaction(sender_id, receiver_id, amount, "FAILED", transaction_type)
            return jsonify({"status": "error", "message": "Failed to deduct amount from sender's wallet"}), 400
        internalToken = generate_jwt(receiver_id)
        receiver_response = requests.post(
            f"{WALLET_SERVICE_BASE_URL}/transaction",
            json={"user_id": receiver_id, "transaction_type": "CREDIT", "amount": amount},
            headers={"Authorization": f"Bearer {internalToken}"},
        )
        print(receiver_response.json())
        if receiver_response.status_code != 200:
            
            transaction_id = record_transaction(sender_id, receiver_id, amount, "FAILED", transaction_type)
            producer.send(
                'refunds',
                {
                    "transaction_id": transaction_id,
                    "sender_id": sender_id,
                    "amount": amount,
                }
            )
            return jsonify({"status": "error", "message": "Failed to credit amount to receiver's wallet. Deducted amount will be refunded to the sender."}), 400

    elif transaction_type == "WALLET_RECHARGE":
        sender_response = requests.post(
            f"{WALLET_SERVICE_BASE_URL}/transaction",
            json={"user_id": sender_id, "transaction_type": "CREDIT", "amount": amount},
            headers={"Authorization": f"Bearer {internalToken}"},
        )

        if sender_response.status_code != 200:
            record_transaction(sender_id, None, amount, "FAILED", transaction_type)
            return jsonify({"status": "error", "message": "Failed to recharge wallet"}), 400

    transaction_id = record_transaction(sender_id, receiver_id, amount, "COMPLETED", transaction_type)
    print("Published to topic")
    return jsonify({"status": "success", "transaction_id": transaction_id}), 200

@routes.route("/transaction/<transaction_id>", methods=["GET"])
def get_transaction_status(transaction_id):

    if not transaction_id:
        return jsonify({"status": "error", "message": "Transaction ID is required"}), 400

    # Fetch transaction status from the database
    transaction = get_transaction_status_db(transaction_id)

    if not transaction:
        return jsonify({"status": "error", "message": "Transaction not found"}), 404

    return jsonify({"status": "success", "data": transaction}), 200