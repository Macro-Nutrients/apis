from google.cloud import firestore
from google.auth import exceptions
from config import Config

# Inisialisasi Firestore client menggunakan Application Default Credentials
def initialize_firestore():
    try:
        db = firestore.Client(project=Config.PROJECT_ID)  # Gunakan ID proyek dari konfigurasi
        print("Firestore client berhasil diinisialisasi.")
        return db
    except exceptions.DefaultCredentialsError as e:
        print(f"Gagal menginisialisasi Firestore: {e}")
        raise

# Fungsi untuk menyimpan data ke Firestore
def store_data(collection, doc_id, data):
    db = initialize_firestore()  # Inisialisasi client Firestore
    doc_ref = db.collection(collection).document(doc_id)  # Menentukan koleksi dan dokumen
    doc_ref.set(data)  # Menyimpan data ke Firestore
    print(f"Data untuk user {doc_id} berhasil disimpan.")
