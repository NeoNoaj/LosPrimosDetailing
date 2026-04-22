from persistencia.api_client import APIClient
from persistencia.modelos import Quote
from negocio.product_service import ProductService

class QuoteService:
    @staticmethod
    def get_user_quotes(user_id):
        quotes_data = APIClient.get_user_quotes(user_id)
        return [Quote(**q) for q in quotes_data]

    @staticmethod
    def create_quote(user_id, service_id, location, comments, size='sedan', dirt='leve'):
        # Obtener precio base real
        product = ProductService.get_product(service_id)
        base_price = getattr(product, 'price', 12000) if product else 12000
        
        # Aplicar multiplicadores
        size_mult = {"sedan": 1.0, "suv": 1.3, "pickup": 1.5, "moto": 0.6}.get(size, 1.0)
        dirt_mult = {"leve": 1.0, "moderada": 1.2, "extrema": 1.6}.get(dirt, 1.0)
        total_price = base_price * size_mult * dirt_mult
        
        # Enriquecer comentarios con metadatos del estimador
        full_comments = f"[{size.upper()} / Suciedad: {dirt.upper()}] {comments}"
        
        result = APIClient.create_quote({
            "user_id": user_id,
            "service_id": service_id,
            "location": location,
            "comments": full_comments,
            "total_price": total_price
        })
        
        if result.get('id') or result.get('success'):
            return True, '¡Solicitud de cotización enviada con éxito!'
        return False, 'Error al crear la cotización.'

    @staticmethod
    def pay_quote(quote_id, method='wallet'):
        result = APIClient.pay_quote(quote_id, method=method)
        if result.get('success'):
            return True, result.get('message', '¡Pago realizado con éxito!')
        else:
            return False, result.get('error', 'Desconocido')
