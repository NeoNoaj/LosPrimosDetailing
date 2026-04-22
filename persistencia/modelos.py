from datetime import datetime

def _parse_date(date_val):
    if not date_val:
        return datetime.utcnow()
    if isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, str):
        try:
            if 'T' in date_val:
                return datetime.fromisoformat(date_val.replace('Z', '+00:00'))
            return datetime.strptime(date_val, '%Y-%m-%d %H:%M:%S')
        except:
            return datetime.utcnow()
    return datetime.utcnow()

class User:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.email = kwargs.get('email')
        self.password = kwargs.get('password')
        self.name = kwargs.get('name')
        self.wallet_balance = kwargs.get('wallet_balance', 0.0)
        self.password_changed_at = _parse_date(kwargs.get('password_changed_at'))
        self.mfa_enabled = bool(kwargs.get('mfa_enabled'))
        self.mfa_secret = kwargs.get('mfa_secret')
        self.is_admin = bool(kwargs.get('is_admin'))
        self.pais = kwargs.get('pais', 'Costa Rica')
        self.provincia = kwargs.get('provincia')
        self.canton = kwargs.get('canton')
        self.distrito = kwargs.get('distrito')
        self.cedula = kwargs.get('cedula')
        self.codelec = kwargs.get('codelec')

    @property
    def vehicles(self):
        from persistencia.api_client import APIClient
        return [Vehicle(**v) for v in APIClient.get_user_vehicles(self.id)]

class Product:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.description = kwargs.get('description', '')
        self.price = kwargs.get('price', 0.0)
        self.category = kwargs.get('category', 'product')
        self.image_url = kwargs.get('image_url')

class Quote:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.user_id = kwargs.get('user_id')
        self.service_id = kwargs.get('service_id')
        self.location = kwargs.get('location', '')
        self.comments = kwargs.get('comments', '')
        self.status = kwargs.get('status', 'pending')
        
        # Parse date from API string
        self.created_at = _parse_date(kwargs.get('created_at'))
        
        # New joined fields from database_service
        self.service_name = kwargs.get('service_name')
        self.service_price = kwargs.get('service_price')
        self.total_price = kwargs.get('total_price', 0.0)

    @property
    def service(self):
        """Helper to return a Product object representing the service."""
        if self.service_name:
            return Product(
                id=self.service_id, 
                name=self.service_name, 
                price=self.service_price, 
                category='service'
            )
        return None

class Review:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.user_id = kwargs.get('user_id')
        self.service_id = kwargs.get('service_id')
        self.rating = kwargs.get('rating', 5)
        self.comment = kwargs.get('comment', '')
        self.created_at = _parse_date(kwargs.get('created_at'))

    @property
    def author(self):
        from persistencia.api_client import APIClient
        user_data = APIClient.get(f"/users/{self.user_id}")
        if user_data:
            return User(**user_data)
        # Fallback author if user not found
        return User(name="Usuario Anónimo")

    @property
    def service(self):
        from persistencia.api_client import APIClient
        service_data = APIClient.get_product(self.service_id)
        if service_data:
            return Product(**service_data)
        # Fallback service if not found
        return Product(name="Servicio General")

class Vehicle:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.plate = kwargs.get('plate')
        self.brand = kwargs.get('brand')
        self.model = kwargs.get('model')
        self.user_id = kwargs.get('user_id')
        self.last_wash = _parse_date(kwargs.get('last_wash'))

    @property
    def images(self):
        from persistencia.api_client import APIClient
        return [GalleryImage(**img) for img in APIClient.get(f"/gallery/vehicle/{self.id}") or []]

class GalleryImage:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.vehicle_id = kwargs.get('vehicle_id')
        self.image_path = kwargs.get('image_path')
        self.uploaded_at = _parse_date(kwargs.get('uploaded_at'))

class WalletTransaction:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.user_id = kwargs.get('user_id')
        self.amount = kwargs.get('amount', 0.0)
        self.description = kwargs.get('description', '')
        self.type = kwargs.get('type', 'credit')
        self.created_at = _parse_date(kwargs.get('created_at'))

class Localidad:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.nombre = kwargs.get('nombre')
        self.tipo = kwargs.get('tipo', 'pais')
        self.id_padre = kwargs.get('id_padre')

class RecoveryToken:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.user_id = kwargs.get('user_id')
        self.token = kwargs.get('token')
        self.created_at = _parse_date(kwargs.get('created_at'))
        self.expires_at = _parse_date(kwargs.get('expires_at'))
        self.used = bool(kwargs.get('used'))
