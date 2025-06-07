from flask import Blueprint, request, jsonify, current_app
import numpy as np
import io
import os
from PIL import Image
import uuid
import json
from google.cloud import firestore
from services.store_data import store_data, initialize_firestore
from config import Config
import jwt

inference_bp = Blueprint('inference', __name__)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(base_dir, 'dataset', 'nutrition_fact.json')

CLASS_NAMES = ["ayam_goreng", "burger", "donat", "kentang_goreng", "mie_goreng"]

def preprocess_image(image_bytes, target_size=(224, 224)):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(target_size)
    arr = np.array(img).astype("float32") / 255.0
    arr = arr.reshape((1,) + arr.shape)  # (1, 224, 224, 3)
    return arr

def decode_jwt(token):
    try:
        # NON-VALIDATED decoding just to read claims
        options = {"verify_exp": False}  # Ini penting!
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'], options=options)
        return payload
    except jwt.InvalidTokenError as e:
        current_app.logger.warning(f"Token invalid: {e}")
        return None

def get_user_id_from_token():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        payload = decode_jwt(token)
        if payload and 'sub' in payload:
            return payload['sub']
    return None

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
        x = preprocess_image(file.read())
        preds = keras_model.predict(x)
        idx = int(np.argmax(preds[0]))
        label = CLASS_NAMES[idx]
        confidence = float(preds[0][idx])
        doc_id = uuid.uuid4().hex

        with open(json_path, 'r', encoding='utf-8') as f:
            nutrition_data = json.load(f)

        nutrition_info = next((item for item in nutrition_data if item.get('name') == label), None)
        if nutrition_info:
            nutrition_info = {
                "name": nutrition_info.get("name").capitalize().replace('_', ' '),
                "calories": str(nutrition_info.get("calories")) + ' kcal',
                "protein": str(nutrition_info.get("protein")) + ' gram',
                "carbohydrates": str(nutrition_info.get("carbohydrates")) + ' gram',
                "fat": str(nutrition_info.get("fat")) + ' gram',
            }

        user_id = get_user_id_from_token()
        login_status = user_id is not None

        if login_status:
            now = firestore.SERVER_TIMESTAMP
            store_data("predictions", doc_id, {
                "user_id": user_id,
                "label": label,
                "confidence": confidence,
                "created_at": now,
                "updated_at": now,
                "facts": nutrition_info,
            })
            current_app.logger.info(f"Prediction stored for user {user_id}")

        return jsonify(
            error=False,
            login=login_status,
            result={
                "label": label,
                "confidence": confidence,
                "facts": nutrition_info,
                "user_id": user_id
            }
        ), 200

    except Exception as e:
        current_app.logger.error(f"[PREDICT ERROR] {e}")
        return jsonify(error=True, message="Gagal melakukan prediksi"), 500

@inference_bp.route('/history', methods=['GET'])
def get_history():
    user_id = get_user_id_from_token()
    if user_id is None:
        return jsonify(error=False, login=False, history=[]), 200

    try:
        db = initialize_firestore()
        docs = db.collection('predictions').where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        history = []
        for doc in docs:
            d = doc.to_dict()
            d['id'] = doc.id
            # Convert Firestore timestamps to ISO 8601 strings if applicable
            if 'created_at' in d and hasattr(d['created_at'], 'isoformat'):
                d['created_at'] = d['created_at'].isoformat()
            if 'updated_at' in d and hasattr(d['updated_at'], 'isoformat'):
                d['updated_at'] = d['updated_at'].isoformat()
            history.append(d)
        return jsonify(error=False, login=True, history=history), 200

    except Exception as e:
        current_app.logger.error(f"Firestore query error: {e}")
        return jsonify(error=True, login=True, message='Gagal mengambil riwayat'), 500

@inference_bp.route('/labels', methods=['GET'])
def get_labels():
    return jsonify(error=False, labels=CLASS_NAMES), 200