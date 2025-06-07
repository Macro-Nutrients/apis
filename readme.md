# 📘 Dokumentasi API Autentikasi – Macro Nutrient

## 📌 Base URL
http://127.0.0.1:5000/

---

## 🔐 Autentikasi JWT

Gunakan token JWT (dikirim via header Authorization) untuk mengakses endpoint yang diproteksi.

**Contoh Header:**
```
Authorization: Bearer <token>
```

---

## 📂 Endpoints

### ✅ POST `/auth/register`
**Deskripsi:** Mendaftarkan user baru dan menyimpan datanya ke Firestore.

#### Request Body
```json
{
  "username": "johndoe",
  "email": "johndoe@example.com",
  "password": "Secure123!"
}
```
**Validasi:**
* Email harus valid.
* Password minimal 8 karakter dan harus mengandung huruf dan angka/simbol.

#### Response - 201 Created
```json
{
  "error": false,
  "message": "User registered successfully"
}
```

#### Response - 400 Bad Request
```json
{
  "error": true,
  "message": "Email invalid / Email already exists / Password weak"
}
```

### 🔓 POST /auth/login
**Deskripsi:** Login dan menghasilkan JWT token.

#### Request Body
```json
{
  "email": "johndoe@example.com",
  "password": "Secure123!"
}
```
#### Response - 200 OK
```json
{
  "error": false,
  "message": "success",
  "result": {
    "userId": "abc123xyz",
    "username": "johndoe",
    "token": "<jwt_token>"
  }
}
```
#### Response - 401 Unauthorized
```json
{
  "error": true,
  "message": "Invalid credentials"
}
```
### 🛡️ GET /auth/
**Deskripsi:** Endpoint yang diproteksi. Mengembalikan ucapan selamat datang.

#### Header
Authorization: Bearer <jwt_token>

#### Response - 200 OK
```json
{
  "message": "Selamat datang, pengguna dengan username johndoe"
}
```
#### Response - 401 Unauthorized
```json
{
  "msg": "Missing Authorization Header / Token invalid"
}
```

### ⚙️ Konfigurasi
```python
from datetime import timedelta

class Config:
    SECRET_KEY = 'BebekGorengH.Slamet'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
```

### 🛠️ Tools Digunakan
* Flask
* Flask-JWT-Extended
* Google Cloud Firestore
* bcrypt
*  Python 3.12+