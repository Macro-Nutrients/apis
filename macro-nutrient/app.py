# FOR LOCAL USE THIS
# import os
# from flask import Flask, g
# from flask_jwt_extended import JWTManager
# from config import Config, CorsConfig
# from google.cloud import firestore
# from google.auth import exceptions
# from routes.auth import auth_bp
# from routes.inference import inference_bp
# from tensorflow.keras.models import load_model
# from google.cloud import storage
# import logging

# # Inisialisasi Firestore client
# try:
#     db = firestore.Client(project=Config.PROJECT_ID)
#     print("Firestore client berhasil diinisialisasi.")
# except exceptions.DefaultCredentialsError as e:
#     print(f"Gagal menginisialisasi Firestore: {e}")

# # Setup Flask app
# app = Flask(__name__)
# app.config.from_object(Config)

# # Setup CORS
# cors = CorsConfig(app=app)

# # Inisialisasi JWT
# jwt = JWTManager(app)

# # Setel variabel lingkungan untuk kredensial Service Account
# # Menggunakan os.path.join untuk membuat path yang lebih portable
# credentials_path = os.path.join(".", "macro-nutrient", "services", "macro-nutrient-2e156a8d27e4.json")

# # Menetapkan path ke environment variable
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
# if os.path.exists(credentials_path):
#     print(f"Kredensial ditemukan di: {credentials_path}")
# else:
#     print(f"Tidak ditemukan kredensial di: {credentials_path}")
# # Setup Google Cloud Storage


# GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "mymlbucket017")

# # Inisialisasi Google Cloud Storage client
# gcs_client = storage.Client()
# bucket = gcs_client.bucket(GCS_BUCKET_NAME)

# # Debug: Cek apakah bucket berhasil diakses
# try:
#     # Coba ambil metadata bucket sebagai tes untuk memastikan koneksi berhasil
#     bucket.exists()  # Cek jika bucket ada dan dapat diakses
#     print(f"[INFO] Google Cloud Storage berhasil diinisialisasi dan bucket '{GCS_BUCKET_NAME}' dapat diakses.")
# except Exception as e:
#     print(f"[ERROR] Gagal mengakses bucket GCS '{GCS_BUCKET_NAME}': {e}")

# # Load Keras model once here
# MODEL_PATH = os.path.join(os.path.dirname(__file__), "model/modelsl_saved_model.keras")
# try:
#     keras_model = load_model(MODEL_PATH)
#     print("[INFO] Model berhasil dimuat di app.py")
# except Exception as e:
#     keras_model = None
#     print(f"[ERROR] Gagal memuat model di app.py: {e}")

    

# # Attach model to app context so it can be accessed from routes
# app.config['KERAS_MODEL'] = keras_model

# # Disable JSON sorting for Flask
# app.json.sort_keys = False

# # Register blueprints
# app.register_blueprint(auth_bp, url_prefix="/auth")
# app.register_blueprint(inference_bp, url_prefix="/inference")

# @app.route('/health', methods=['GET'])
# def health_check():
#     """Route untuk cek status API"""
#     return {"status": "OK"}, 200

# if __name__ == "__main__":
#     port = int(os.getenv("PORT", 8080))
#     app.run(host="0.0.0.0", port=port, debug=True)

#for cloud run dont mind it
import os
from flask import Flask
from flask_jwt_extended import JWTManager
from config import Config, CorsConfig
from google.cloud import firestore, storage
from google.auth import exceptions
from routes.auth import auth_bp
from routes.inference import inference_bp
from tensorflow.keras.models import load_model
import logging

app = Flask(__name__)
app.config.from_object(Config)
cors = CorsConfig(app=app)
jwt = JWTManager(app)

# Detect if running locally or on Cloud Run by env var
RUNNING_LOCALLY = os.getenv("RUNNING_LOCALLY", "false").lower() == "true"

if RUNNING_LOCALLY:
    # For local Windows dev: set path to your JSON key file (adjust path if needed)
    credentials_path = os.path.join(".", "services", "macro-nutrient-2e156a8d27e4.json")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    print(f"[INFO] Running locally. Using credentials from: {credentials_path}")
else:
    # Cloud Run: use Application Default Credentials (no JSON file needed)
    print("[INFO] Running on Cloud Run. Using Application Default Credentials.")

# Initialize Firestore client
try:
    db = firestore.Client()
    print("[INFO] Firestore client initialized successfully.")
except exceptions.DefaultCredentialsError as e:
    print(f"[ERROR] Failed to initialize Firestore: {e}")

# Initialize Google Cloud Storage client
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "mymlbucket017")
try:
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(GCS_BUCKET_NAME)
    bucket.exists()  # Trigger API call to verify access
    print(f"[INFO] GCS client initialized. Bucket '{GCS_BUCKET_NAME}' accessible.")
except Exception as e:
    print(f"[ERROR] Failed to access GCS bucket '{GCS_BUCKET_NAME}': {e}")

# Load Keras model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "modelsl_saved_model.keras")
try:
    keras_model = load_model(MODEL_PATH)
    print("[INFO] Keras model loaded successfully.")
except Exception as e:
    keras_model = None
    print(f"[ERROR] Failed to load Keras model: {e}")

app.config["KERAS_MODEL"] = keras_model
app.json.sort_keys = False

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(inference_bp, url_prefix="/inference")

@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "OK"}, 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)