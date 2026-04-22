import requests
import os

class BankingService:
    BANK_URL = os.environ.get('BANK_SERVICE_URL', "https://practical-albattani.138-59-135-33.plesk.page/api")
    LOCAL_DB_URL = os.environ.get('DATABASE_SERVICE_URL', "http://127.0.0.1:3000/api")

    @classmethod
    def get_linked_card(cls, user_id):
        """Busca en el servicio local si el usuario tiene una tarjeta vinculada."""
        try:
            response = requests.get(f"{cls.LOCAL_DB_URL}/payment-method/{user_id}", timeout=3)
            if response.status_code == 200:
                return response.json().get('card')
            return None
        except:
            return None

    @classmethod
    def link_card(cls, user_id, holder, number, cvv, expiry):
        """Llama al servicio local para verificar y vincular una tarjeta."""
        try:
            response = requests.post(f"{cls.LOCAL_DB_URL}/payment-method", json={
                "user_id": user_id,
                "card_holder": holder,
                "card_number": number,
                "cvv": cvv,
                "expiry_date": expiry
            }, timeout=10)
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def get_account_details(cls, account_id):
        """Obtiene detalles de una cuenta específica desde el banco."""
        try:
            # Reutilizamos el endpoint existente filtrando por ID
            response = requests.get(f"{cls.BANK_URL}/cuentas", timeout=5)
            if response.status_code == 200:
                for acc in response.json():
                    if acc['id'] == account_id:
                        return acc
            return None
        except:
            return None

    @classmethod
    def get_movements_by_account_id(cls, account_id):
        """Obtiene movimientos de una cuenta bancaria."""
        try:
            response = requests.get(f"{cls.BANK_URL}/movimientos", params={"cuenta_id": account_id}, timeout=5)
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []

    @classmethod
    def unlink_card(cls, user_id):
        """Elimina la vinculación de la tarjeta en el servicio local."""
        try:
            response = requests.delete(f"{cls.LOCAL_DB_URL}/payment-method/{user_id}", timeout=5)
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def check_health(cls):

        """Verifica salud de ambos servicios."""
        status = {"bank": False, "local": False}
        try:
            status["bank"] = requests.get(f"{cls.BANK_URL}/cuentas", timeout=1).status_code == 200
        except: pass
        try:
            status["local"] = requests.get(f"{cls.LOCAL_DB_URL}/tipo-cambio", timeout=1).status_code == 200
        except: pass
        return status
