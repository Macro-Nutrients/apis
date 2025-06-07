from flask import Blueprint, request, jsonify, current_app
import numpy as np
import io
from PIL import Image
import uuid
from tensorflow.keras.preprocessing.image import img_to_array
from google.cloud import firestore
from services.store_data import store_data
from services.store_image import ImageStorageService
import json


inference_bp = Blueprint('inference', __name__)

image_service = ImageStorageService(bucket_name='nama-bucket')


CLASS_NAMES = ["ayam_goreng", "burger", "donat", "kentang_goreng", "mie_goreng"]

def preprocess_image(image_bytes, target_size=(224, 224)):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(target_size)
    arr = img_to_array(img).astype("float32") / 255.0
    return np.expand_dims(arr, axis=0)

@inference_bp.route('/predict', methods=['POST'])
def predict():
    keras_model = current_app.config.get('KERAS_MODEL')
    if keras_model is None:
        return jsonify(error=True, message="Model belum tersedia"), 500

    if 'image' not in request.files:
        return jsonify(error=True, message="Key 'image' tidak ditemukan"), 400

    file = request.files['image']
    if file.filename == "":
        return jsonify(error=True, message="Nama file kosong"), 400
    
    try:
        filename, url = image_service.upload_image(file)
        x = preprocess_image(file.read())
        preds = keras_model.predict(x)
        idx = int(np.argmax(preds[0]))
        label = CLASS_NAMES[idx]
        confidence = float(preds[0][idx])

        doc_id = uuid.uuid4().hex

        with open('dataset/nutrition_fact.json', 'r', encoding='utf-8') as f:
            nutrition_data = json.load(f)

        nutrition_info = next((item for item in nutrition_data if item.get('name') == label), None)
        
        # Mutasi object nutrition_info jika ditemukan
        if nutrition_info:
            nutrition_info = {
                "name": nutrition_info.get("name").capitalize().replace('_', ' '),
                "calories": str(nutrition_info.get("calories")) + ' kcal ',
                "protein": str(nutrition_info.get("protein")) + ' gram',
                "carbohydrates": str(nutrition_info.get("carbohydrates")) + ' gram',
                "fat": str(nutrition_info.get("fat")) + ' gram',
            }

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

        return jsonify(error=False, result={"label": label, "confidence": confidence, "facts":nutrition_info, "filename":filename, "public_url":url}), 200
    except Exception as e:
        current_app.logger.error(f"[PREDICT ERROR] {e}")
        return jsonify(error=True, message="Gagal melakukan prediksi"), 500

@inference_bp.route('/labels', methods=['GET'])
def get_labels():
    return jsonify(error=False, labels=CLASS_NAMES), 200
