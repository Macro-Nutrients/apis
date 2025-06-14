# config.pyAdd commentMore actions

import os
from flask_cors import CORS
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'BebekGorengH.Slamet')  # Akan override lewat --set-env-vars
    PROJECT_ID = 'macro-nutrient'
    DATABASE_ID = 'macronutrient'
    
class CorsConfig:
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        # Konfigurasi CORS global
        CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)