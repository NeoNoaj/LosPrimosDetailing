from persistencia.api_client import APIClient
from persistencia.modelos import Product, Review

class ProductService:
    @staticmethod
    def get_all_products():
        products_data = APIClient.get_products()
        return [Product(**p) for p in products_data]

    @staticmethod
    def get_all_services():
        products_data = APIClient.get_products()
        return [Product(**p) for p in products_data if p.get('category') == 'service']

    @staticmethod
    def get_product(product_id):
        product_data = APIClient.get_product(product_id)
        return Product(**product_data) if product_data else None

    @staticmethod
    def get_reviews():
        reviews_data = APIClient.get_reviews()
        return [Review(**r) for r in reviews_data]

    @staticmethod
    def create_review(user_id, service_id, rating, comment):
        if not rating or not comment or not service_id:
            return False, 'Por favor, proporcione una calificación, un comentario y seleccione un servicio.'
        
        result = APIClient.create_review({
            "user_id": user_id,
            "service_id": service_id,
            "rating": int(rating),
            "comment": comment
        })
        return True, '¡Reseña publicada con éxito!'
