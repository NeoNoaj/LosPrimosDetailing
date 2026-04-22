import requests
import os

class APIClient:
    BASE_URL = os.environ.get('DATABASE_SERVICE_URL')

    @classmethod
    def get(cls, endpoint, params=None):
        try:
            response = requests.get(f"{cls.BASE_URL}{endpoint}", params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API Error (GET {endpoint}): {e}")
            return None

    @classmethod
    def post(cls, endpoint, data):
        try:
            response = requests.post(f"{cls.BASE_URL}{endpoint}", json=data, timeout=5)
            if not response.ok:
                try:
                    error_data = response.json()
                    return {"error": error_data.get('error', response.reason), "success": False}
                except:
                    return {"error": response.reason, "success": False}
            return response.json()
        except Exception as e:
            print(f"API Error (POST {endpoint}): {e}")
            return {"error": str(e), "success": False}

    @classmethod
    def put(cls, endpoint, data):
        try:
            response = requests.put(f"{cls.BASE_URL}{endpoint}", json=data, timeout=5)
            if not response.ok:
                try:
                    error_data = response.json()
                    return {"error": error_data.get('error', response.reason), "success": False}
                except:
                    return {"error": response.reason, "success": False}
            return response.json()
        except Exception as e:
            print(f"API Error (PUT {endpoint}): {e}")
            return {"error": str(e), "success": False}

    @classmethod
    def delete(cls, endpoint):
        try:
            response = requests.delete(f"{cls.BASE_URL}{endpoint}", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API Error (DELETE {endpoint}): {e}")
            return {"error": str(e), "success": False}

    # -- High level methods for specific entities --

    # Users
    @classmethod
    def get_user_by_email(cls, email):
        return cls.get(f"/users/email/{email}")

    @classmethod
    def get_user_by_id(cls, user_id):
        return cls.get(f"/users/{user_id}")

    @classmethod
    def create_user(cls, user_data):
        return cls.post("/users", user_data)

    @classmethod
    def update_user(cls, user_id, user_data):
        return cls.put(f"/users/{user_id}", user_data)

    # Products
    @classmethod
    def get_products(cls):
        return cls.get("/products") or []

    @classmethod
    def get_product(cls, product_id):
        return cls.get(f"/products/{product_id}")

    # Vehicles
    @classmethod
    def get_user_vehicles(cls, user_id):
        return cls.get(f"/vehicles/user/{user_id}") or []

    @classmethod
    def get_vehicle_by_plate(cls, plate):
        return cls.get(f"/vehicles/plate/{plate}")

    @classmethod
    def create_vehicle(cls, vehicle_data):
        return cls.post("/vehicles", vehicle_data)

    # Quotes
    @classmethod
    def get_user_quotes(cls, user_id):
        return cls.get(f"/quotes/user/{user_id}") or []

    @classmethod
    def create_quote(cls, quote_data):
        return cls.post("/quotes", quote_data)

    @classmethod
    def pay_quote(cls, quote_id, method='wallet'):
        return cls.post(f"/quotes/{quote_id}/pay", {"method": method})

    # Reviews
    @classmethod
    def get_reviews(cls):
        return cls.get("/reviews") or []

    @classmethod
    def create_review(cls, review_data):
        return cls.post("/reviews", review_data)

    # Localidades
    @classmethod
    def get_localidades(cls, tipo=None, id_padre=None):
        params = {}
        if tipo: params['tipo'] = tipo
        if id_padre: params['id_padre'] = id_padre
        return cls.get("/localidades", params=params) or []

    # Wallet
    @classmethod
    def get_user_transactions(cls, user_id):
        return cls.get(f"/transactions/user/{user_id}") or []

    @classmethod
    def create_transaction(cls, transaction_data):
        return cls.post("/transactions", transaction_data)

    # Security
    @classmethod
    def log_audit(cls, user_id, action, ip, details):
        return cls.post("/audit-logs", {
            "user_id": user_id,
            "action": action,
            "ip_address": ip,
            "details": details
        })

    @classmethod
    def get_password_history(cls, user_id):
        return cls.get(f"/password-history/user/{user_id}") or []

    @classmethod
    def add_password_history(cls, user_id, password_hash):
        return cls.post("/password-history", {"user_id": user_id, "password_hash": password_hash})

    @classmethod
    def create_recovery_token(cls, user_id, token, expires_at):
        return cls.post("/recovery-tokens", {"user_id": user_id, "token": token, "expires_at": expires_at.isoformat()})

    @classmethod
    def get_recovery_token(cls, token):
        return cls.get(f"/recovery-tokens/{token}")

    @classmethod
    def use_recovery_token(cls, token):
        return cls.put(f"/recovery-tokens/{token}", {"used": True})
