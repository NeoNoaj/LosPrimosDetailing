from persistencia.api_client import APIClient

class LoyaltyService:
    @staticmethod
    def get_user_loyalty_status(user_id):
        try:
            history = APIClient.get(f"/user-history/{user_id}")
            if not history:
                return None, "No se encontró historial"
            
            total_spent = sum(t['amount'] for t in history.get('billing', []))
            visit_count = len(history.get('services', []))
            
            tier = "BRONCE"
            if visit_count >= 10: tier = "PLATINO"
            elif visit_count >= 5: tier = "ORO"
            elif visit_count >= 2: tier = "PLATA"
            
            return {
                "estatus": tier,
                "visitas_registradas": visit_count,
                "beneficio_actual": f"{15 if tier == 'PLATINO' else 10 if tier == 'ORO' else 5 if tier == 'PLATA' else 0}% de descuento"
            }, None
        except Exception as e:
            return None, str(e)
