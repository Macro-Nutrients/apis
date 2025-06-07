import uuid
from google.cloud import storage

class ImageStorageService:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(bucket_name)

    def upload_image(self, file):
        """Fungsi untuk mengupload gambar ke GCS dan mengembalikan URL publik"""
        ext = file.filename.rsplit('.', 1)[-1]
        unique_filename = f"{uuid.uuid4()}.{ext}"

        blob = self.bucket.blob(unique_filename)
        blob.upload_from_file(file, content_type=file.content_type)
        blob.make_public()
        url = blob.public_url

        return {
            'filename': unique_filename,
            'url': url
        }