import re
import os
import bcrypt
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from persistencia.api_client import APIClient

# Encryption Setup
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = "IUFFt3JEvVFTq2l_VTOO0dr2WeeUG9iIVvq4sR1bsiE=" 
    if os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError("ENCRYPTION_KEY must be set in production environment.")

try:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
except Exception as e:
    print(f"CRITICAL: Invalid ENCRYPTION_KEY. Generating temporary key. {str(e)}")
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())

class SecurityUtils:
    @staticmethod
    def validate_password_policy(password):
        if len(password) < 12:
            return False, "La contraseña debe tener al menos 12 caracteres."
        if not re.search(r"[A-Z]", password):
            return False, "La contraseña debe contener al menos una letra mayúscula."
        if not re.search(r"[a-z]", password):
            return False, "La contraseña debe contener al menos una letra minúscula."
        if not re.search(r"\d", password):
            return False, "La contraseña debe contener al menos un número."
        if not re.search(r"[ !@#$%^&*(),.?\":{}|<>]", password):
            return False, "La contraseña debe contener al menos un símbolo especial."
        return True, ""

    @staticmethod
    def hash_password(password):
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def check_password(password, hashed):
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False

    @staticmethod
    def is_password_reused(user_id, new_password, months=9):
        """
        Check if password was used in history via API.
        """ 
        history = APIClient.get_password_history(user_id)
        for hashed_pw in history:
            if SecurityUtils.check_password(new_password, hashed_pw):
                return True
        return False

    @staticmethod
    def encrypt_data(data):
        if not data: return None
        return cipher_suite.encrypt(data.encode()).decode()

    @staticmethod
    def decrypt_data(encrypted_data):
        if not encrypted_data: return None
        try:
            return cipher_suite.decrypt(encrypted_data.encode()).decode()
        except Exception:
            return None

    @staticmethod
    def log_event(user_id, action, ip_address, details=None):
        """
        Audit Log via API.
        """
        APIClient.log_audit(user_id, action, ip_address, details)
