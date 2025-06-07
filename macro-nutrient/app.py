# app.py
import os
from flask import Flask, g
from flask_jwt_extended import JWTManager
from config import Config, CorsConfig
from google.cloud import firestore
from google.auth import exceptions
from routes.auth import auth_bp
from routes.inference import inference_bp
from tensorflow.keras.models import load_model

# Inisialisasi Firestore client
try:
    db = firestore.Client(project=Config.PROJECT_ID)
    print("Firestore client berhasil diinisialisasi.")
except exceptions.DefaultCredentialsError as e:
    print(f"Gagal menginisialisasi Firestore: {e}")

# Setup Flask app
app = Flask(__name__)
app.config.from_object(Config)

# setup CORS
cors = CorsConfig(app=app)

# Inisialisasi JWT
jwt = JWTManager(app)

# Load Keras model once here
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model/modelsl_saved_model.keras")
try:
    keras_model = load_model(MODEL_PATH)
    print("[INFO] Model berhasil dimuat di app.py")
except Exception as e:
    keras_model = None
    print(f"[ERROR] Gagal memuat model di app.py: {e}")

# Attach model to app context so it can be accessed from routes
app.config['KERAS_MODEL'] = keras_model

# Register blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(inference_bp, url_prefix="/inference")

@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "OK"}, 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)