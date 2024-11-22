import jwt
import datetime
import os

SECRET_KEY = os.getenv("INTERNAL_SECRET_PHRASE")

def generate_jwt(user_id):

    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        "iat": datetime.datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token