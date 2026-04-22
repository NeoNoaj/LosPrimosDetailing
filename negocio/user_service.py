from persistencia.api_client import APIClient
from persistencia.modelos import User, WalletTransaction

class UserService:
    @staticmethod
    def get_user_by_id(user_id):
        user_data = APIClient.get_user_by_id(user_id)
        return User(**user_data) if user_data else None

    @staticmethod
    def recharge_wallet(user_id, amount):
        user_data = APIClient.get_user_by_id(user_id)
        if not user_data:
            return False, "Usuario no encontrado"

        user = User(**user_data)
        if not amount or amount <= 0:
            return False, "Monto de recarga inválido."

        new_balance = (user.wallet_balance or 0) + amount
        update_success = APIClient.update_user(user.id, {"wallet_balance": new_balance})
        
        if update_success.get('success', True): # Assuming APIClient returns dict on put or just json, APIClient.update_user returns response.json()
            APIClient.create_transaction({
                "user_id": user.id,
                "amount": amount,
                "description": "Recarga de saldo",
                "type": "credit"
            })
            return True, f"¡Recarga de ₡{amount} realizada con éxito!"
        return False, "Error al actualizar el saldo."

    @staticmethod
    def get_user_transactions(user_id, filter_keyword=None):
        all_transactions = APIClient.get_user_transactions(user_id)
        transactions = []
        for t in all_transactions:
            if filter_keyword:
                if filter_keyword.lower() in t.get('description', '').lower():
                    transactions.append(WalletTransaction(**t))
            else:
                transactions.append(WalletTransaction(**t))
        return transactions

    @staticmethod
    def get_localidades(tipo=None, provincia=None, canton=None):
        params = {}
        if tipo: params['tipo'] = tipo
        if provincia: params['provincia'] = provincia
        if canton: params['canton'] = canton
        return APIClient.get("/localidades", params=params) or []

    @staticmethod
    def get_padron(cedula):
        return APIClient.get(f"/padron/{cedula}")
