import os
from flask import Blueprint, request, jsonify, current_app
import numpy as np
import io
from PIL import Image
import uuid
from services.store_data import store_data, initialize_firestore
from tensorflow.keras.preprocessing.image import img_to_array
from google.cloud import firestore, storage
import json
import google.auth

# Inisialisasi GCS client
gcs_client = storage.Client()
bucket = gcs_client.bucket("mymlbucket017")  # Ganti dengan nama bucket yang sesuai

# Blueprint untuk inference
inference_bp = Blueprint('inference', __name__)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(base_dir, 'dataset', 'nutrition_fact.json')

CLASS_NAMES = ["ayam_goreng", "burger", "donat", "kentang_goreng", "mie_goreng"]

# Fungsi untuk memproses gambar yang diterima
def preprocess_image(image_bytes, target_size=(224, 224)):
    """Fungsi untuk memproses gambar yang diterima menjadi format yang dapat diterima model Keras"""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(target_size)
    arr = img_to_array(img).astype("float32") / 255.0
    return np.expand_dims(arr, axis=0)

# Fungsi untuk upload gambar ke GCS
def upload_image_to_gcs(file, folder_name="images"):
    try:
        # Membuat folder 'images/'
        folder = f"{folder_name}/"
        
        # Membuat nama file unik menggunakan UUID
        filename = f"{folder}{uuid.uuid4()}_{file.filename}"
        
        # Mengupload file ke GCS
        blob = bucket.blob(filename)
        file.seek(0)  # Reset file pointer ke awal setelah membaca ukuran
        blob.upload_from_file(file)
        
        # Membuat file menjadi publik
        # Pastikan Anda menonaktifkan `make_public()` jika Uniform Bucket-Level Access diaktifkan
        # blob.make_public()
        
        # Mengembalikan nama file dan URL publik
        return filename, blob.public_url
    except Exception as e:
        current_app.logger.error(f"[GCS ERROR] Gagal mengupload gambar ke GCS: {e}")
        return None, None

# Route untuk prediksi
@inference_bp.route('/predict', methods=['POST'])
def predict():
    try:
        # Memuat model dari konfigurasi aplikasi Flask
        keras_model = current_app.config.get('KERAS_MODEL')
        if keras_model is None:
            return jsonify(error=True, message="Model belum tersedia"), 500
        current_app.logger.info("Model berhasil dimuat")

        # Mengecek apakah file gambar ada dalam request
        if 'image' not in request.files:
            return jsonify(error=True, message="Key 'image' tidak ditemukan"), 400

        file = request.files['image']
        if file.filename == "":
            return jsonify(error=True, message="Nama file kosong"), 400

        # Menambahkan logging untuk memulai proses prediksi
        current_app.logger.info("Mempersiapkan gambar untuk prediksi...")
        x = preprocess_image(file.read())
        current_app.logger.info("Gambar telah diproses, melakukan prediksi...")

        # Melakukan prediksi
        preds = keras_model.predict(x)
        idx = int(np.argmax(preds[0]))
        label = CLASS_NAMES[idx]
        confidence = float(preds[0][idx])

        current_app.logger.info(f"Prediksi selesai. Label: {label}, Confidence: {confidence}")

        # Muat data nutrisi
        with open(json_path, 'r', encoding='utf-8') as f:
            nutrition_data = json.load(f)

        nutrition_info = next((item for item in nutrition_data if item.get('name') == label), None)
        
        if nutrition_info:
            nutrition_info = {
                "name": nutrition_info.get("name").capitalize().replace('_', ' '),
                "calories": str(nutrition_info.get("calories")) + ' kcal ',
                "protein": str(nutrition_info.get("protein")) + ' gram',
                "carbohydrates": str(nutrition_info.get("carbohydrates")) + ' gram',
                "fat": str(nutrition_info.get("fat")) + ' gram',
            }

        # Upload gambar ke GCS setelah prediksi selesai
        filename, url = upload_image_to_gcs(file)
        if filename is None or url is None:
            return jsonify(error=True, message="Gagal mengupload gambar"), 500

        # Simpan data prediksi ke Firestore
        doc_id = uuid.uuid4().hex
        store_data("predictions", doc_id, {
            "label": label,
            "confidence": confidence,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "facts": nutrition_info,
            "image": {
                "filename": filename,
                "url": url
            }
        })

        # Mengembalikan hasil prediksi
        return jsonify(error=False, result={
            "label": label,
            "confidence": confidence,
            "facts": nutrition_info,
            "filename": filename,
            "public_url": url
        }), 200

    except Exception as e:
        current_app.logger.error(f"[PREDICT ERROR] {e}")
        return jsonify(error=True, message="Gagal melakukan prediksi"), 500

# Route untuk mendapatkan daftar label
@inference_bp.route('/labels', methods=['GET'])
def get_labels():
    """Route untuk mendapatkan daftar label yang tersedia untuk prediksi"""
    return jsonify(error=False, labels=CLASS_NAMES), 200
