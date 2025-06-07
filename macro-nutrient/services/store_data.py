from google.cloud import firestore
from google.auth import exceptions
from config import Config

_db = None

def initialize_firestore():
    global _db
    if _db is not None:
        return _db
    try:
        _db = firestore.Client(project=Config.PROJECT_ID)
        print("Firestore client berhasil diinisialisasi.")
        return _db
    except exceptions.DefaultCredentialsError as e:
        print(f"Gagal menginisialisasi Firestore: {e}")
        raise

def store_data(collection, doc_id, data):
    db = initialize_firestore()
    doc_ref = db.collection(collection).document(doc_id)
    doc_ref.set(data)
    print(f"Data untuk dokumen {doc_id} berhasil disimpan di koleksi {collection}.")

def get_user_predictions(user_id):
    db = initialize_firestore()
    docs = db.collection("predictions")\
             .where("user_id", "==", user_id)\
             .order_by("created_at", direction=firestore.Query.DESCENDING)\
             .stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        results.append(data)
    return results