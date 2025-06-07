# routes/auth.py

import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from google.cloud import firestore

auth_bp = Blueprint('auth', __name__)
db = firestore.Client(project="macro-nutrient")  # Ubah sesuai ID proyek GCP kamu jika beda

def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def is_valid_password(password):
    return re.match(r'^(?=.*[A-Za-z])(?=.*[\d\W])[A-Za-z\d\W]{8,}$', password)

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')

        if not email or not username or not password:
            return jsonify(error=True, message="Email, username, dan password wajib diisi"), 400
        if not is_valid_email(email):
            return jsonify(error=True, message="Format email tidak valid"), 400
        if not is_valid_password(password):
            return jsonify(error=True, message="Password minimal 8 karakter, kombinasi huruf dan angka/simbol"), 400

        users_ref = db.collection('users')
        existing_user = users_ref.where('email', '==', email).get()
        if existing_user:
            return jsonify(error=True, message="Email sudah terdaftar"), 400

        hashed_pw = generate_password_hash(password)
        users_ref.add({"username": username, "email": email, "password": hashed_pw})
        return jsonify(error=False, message="Registrasi berhasil"), 201

    except Exception as e:
        print(f"[REGISTER ERROR] {e}")
        return jsonify(error=True, message="Terjadi kesalahan server"), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify(error=True, message="Email dan password wajib diisi"), 400

        users_ref = db.collection('users')
        snapshot = users_ref.where('email', '==', email).get()
        if not snapshot:
            return jsonify(error=True, message="Email atau password salah"), 401

        user_doc = snapshot[0]
        user = user_doc.to_dict()

        if not check_password_hash(user['password'], password):
            return jsonify(error=True, message="Email atau password salah"), 401

        token = create_access_token(identity=user['username'])

        return jsonify(error=False, message="Login berhasil", result={
            "userId": user_doc.id,
            "username": user['username'],
            "token": token
        }), 200

    except Exception as e:
        print(f"[LOGIN ERROR] {e}")
        return jsonify(error=True, message="Terjadi kesalahan server"), 500

@auth_bp.route('/', methods=['GET'])
@jwt_required()
def protected():
    username = get_jwt_identity()
    return jsonify(message=f"Selamat datang, {username}"), 200
