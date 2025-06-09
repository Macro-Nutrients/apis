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
import jwt
from datetime import datetime

# Inisialisasi GCS client
gcs_client = storage.Client()
bucket = gcs_client.bucket("mymlbucket017")

# Blueprint untuk inference
inference_bp = Blueprint('inference', __name__)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(base_dir, 'dataset', 'nutrition_fact.json')

CLASS_NAMES = ["ayam_goreng", "burger", "donat", "kentang_goreng", "mie"]

def format_timestamp(ts):
    """
    Format Firestore timestamp ke string dd/mm/yyyy HH:MM:SS
    Jika ts None atau bukan timestamp, kembalikan None
    """
    if ts is None:
        return None
    try:
        # Jika objek ts punya method to_datetime() (Firestore Timestamp)
        if hasattr(ts, 'to_datetime'):
            dt = ts.to_datetime()
        # Jika sudah datetime langsung pakai
        elif isinstance(ts, datetime):
            dt = ts
        else:
            return None
        return dt.strftime('%d/%m/%Y %H:%M:%S')
    except Exception:
        return None

# Fungsi untuk memproses gambar
def preprocess_image(image_bytes, target_size=(224, 224)):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(target_size)
    arr = img_to_array(img).astype("float32") / 255.0
    return np.expand_dims(arr, axis=0)

# Upload gambar ke GCS
def upload_image_to_gcs(file, folder_name="images"):
    try:
        folder = f"{folder_name}/"
        filename = f"{folder}{uuid.uuid4()}_{file.filename}"
        blob = bucket.blob(filename)
        file.seek(0)
        blob.upload_from_file(file, content_type=file.content_type)
        blob.make_public()
        return filename, blob.public_url
    except Exception as e:
        current_app.logger.error(f"[GCS ERROR] Gagal mengupload gambar ke GCS: {e}")
        return None, None

# Fungsi decode JWT sesuai permintaan
def decode_jwt(token):
    try:
        options = {"verify_exp": False}
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'], options=options)
        return payload
    except jwt.InvalidTokenError as e:
        current_app.logger.warning(f"Token invalid: {e}")
        return None

# Fungsi ambil user id dari header Authorization pakai decode_jwt
def get_user_id_from_token():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        payload = decode_jwt(token)
        if payload and 'sub' in payload:
            return payload['sub']
    return None

# Endpoint predict
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
        confidence_percent = round(confidence * 100, 2)  # jadi persen
        confidence_with_percent = f"{confidence_percent}%"

        # Threshold pengecekan confidence minimal 85%
        if confidence_percent < 85:
            return jsonify(error=True, message="Gambar yang diinput bukan makanan. Mohon input gambar kembali."), 400

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
                "gi": nutrition_info.get("gi"),  # glycemic index jika ada
                "gl": nutrition_info.get("gl"),  # glycemic load jika ada
            }

        user_id = get_user_id_from_token()
        login_status = user_id is not None

        filename = None
        url = None

        if login_status:
            file.seek(0)
            filename, url = upload_image_to_gcs(file)
            if filename is None or url is None:
                return jsonify(error=True, message="Gagal mengupload gambar"), 500

            now = firestore.SERVER_TIMESTAMP
            store_data("predictions", doc_id, {
                "user_id": user_id,
                "label": label,
                "confidence": confidence_percent,
                "created_at": now,
                "updated_at": now,
                "facts": nutrition_info,
                "image": {
                    "filename": filename,
                    "public_url": url
                }
            })
            current_app.logger.info(f"Prediction stored for user {user_id}")

        response_result = {
            "label": label,
            "confidence": confidence_with_percent,
            "facts": nutrition_info,
            "user_id": user_id
        }

        if login_status:
            now_str = datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')
            response_result.update({
                "id": doc_id,
                "filename": filename,
                "public_url": url,
                "created_at": now_str,
                "updated_at": now_str,
            })

        return jsonify(
            error=False,
            login=login_status,
            result=response_result
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
        docs = db.collection('predictions')\
            .where('user_id', '==', user_id)\
            .order_by('created_at', direction=firestore.Query.DESCENDING)\
            .stream()

        history = []
        for doc in docs:
            d = doc.to_dict()
            d['id'] = doc.id

            # Format created_at dan updated_at ke string format dd/mm/yyyy HH:MM:SS
            d['created_at'] = format_timestamp(d.get('created_at'))
            d['updated_at'] = format_timestamp(d.get('updated_at'))

            if 'image' in d and isinstance(d['image'], dict):
                d['public_url'] = d['image'].get('public_url')
                d['filename'] = d['image'].get('filename')

            history.append(d)

        return jsonify(error=False, login=True, history=history), 200

    except Exception as e:
        current_app.logger.error(f"Firestore query error: {e}")
        return jsonify(error=True, login=True, message='Gagal mengambil riwayat'), 500


# Get prediction by ID
@inference_bp.route('/<prediction_id>', methods=['GET'])
def get_prediction_by_id(prediction_id):
    try:
        db = initialize_firestore()
        doc_ref = db.collection("predictions").document(prediction_id)
        doc = doc_ref.get()

        if not doc.exists:
            return jsonify(error=True, message="Data tidak ditemukan"), 404

        data = doc.to_dict()
        data['id'] = doc.id
        return jsonify(error=False, result=data), 200

    except Exception as e:
        current_app.logger.error(f"[GET BY ID ERROR] {e}")
        return jsonify(error=True, message="Gagal mengambil data"), 500

# Get available labels
@inference_bp.route('/labels', methods=['GET'])
def get_labels():
    return jsonify(error=False, labels=CLASS_NAMES), 200