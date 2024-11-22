from flask import Flask
from routes import routes
from db import initialize_db
from dotenv import load_dotenv

app = Flask(__name__)

initialize_db()
load_dotenv()

app.register_blueprint(routes)

if __name__ == "__main__":

    app.run(host="127.0.0.1", port=8080, debug=True)
