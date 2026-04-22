import os
import re

file_path = r'c:\Users\joans\Downloads\AplicacionMovil\presentacion\rutas\main.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports
content = content.replace(
    "from persistencia.modelos import User, Product, Review, Quote, GalleryImage, Vehicle, WalletTransaction",
    "from persistencia.modelos import User, Product, Review, Quote, GalleryImage, Vehicle, WalletTransaction\nfrom negocio.user_service import UserService\nfrom negocio.product_service import ProductService\nfrom negocio.quote_service import QuoteService\nfrom negocio.loyalty_service import LoyaltyService"
)

content = content.replace(
    "from persistencia.api_client import APIClient",
    ""
)

content = content.replace(
    "from negocio.vehicle_service import get_user_vehicles, register_vehicle",
    "from negocio.vehicle_service import get_user_vehicles, register_vehicle, get_vehicle, add_gallery_image"
)

# 2. Replacing APIClient.get_user_by_id(...) -> UserService.get_user_by_id(...)
# But wait, UserService.get_user_by_id returns a User object. The old code does:
# user_data = APIClient.get_user_by_id(session['user_id'])
# if user_data:
#     user = User(**user_data)
# Let's replace the whole blocks.

content = re.sub(
    r"user_data = APIClient\.get_user_by_id\((.*?)\)\s+if user_data:\s+user = User\(\*\*user_data\)",
    r"user = UserService.get_user_by_id(\1)\n        if user:",
    content
)

content = re.sub(
    r"user_data = APIClient\.get_user_by_id\((.*?)\)\s+user = User\(\*\*user_data\)",
    r"user = UserService.get_user_by_id(\1)",
    content
)

# Replace remaining APIClient.get_user_by_id if any:
content = content.replace("APIClient.get_user_by_id(", "UserService.get_user_by_id(")
content = content.replace("user = User(**user_data) if user_data else None", "user = user_data")

# 3. Products
content = content.replace(
    "products_data = APIClient.get_products()\n    products = [Product(**p) for p in products_data]",
    "products = ProductService.get_all_products()"
)

content = re.sub(
    r"product_data = APIClient\.get_product\((.*?)\)\s+if not product_data:\s+return \"Producto no encontrado\", 404\s+product = Product\(\*\*product_data\)",
    r"product = ProductService.get_product(\1)\n    if not product:\n        return \"Producto no encontrado\", 404",
    content
)

content = content.replace(
    "products_data = APIClient.get_products()\n    services = [Product(**p) for p in products_data if p['category'] == 'service']",
    "services = ProductService.get_all_services()"
)


# 4. Wallet recharge
content = content.replace(
    """    if amount and amount > 0:
        new_balance = (user.wallet_balance or 0) + amount
        APIClient.update_user(user.id, {"wallet_balance": new_balance})
        
        APIClient.create_transaction({
            "user_id": user.id,
            "amount": amount,
            "description": "Recarga de saldo",
            "type": "credit"
        })
        flash(f'¡Recarga de ₡{amount} realizada con éxito!', 'success')
    else:
        flash('Monto de recarga inválido.', 'error')""",
    """    success, msg = UserService.recharge_wallet(user.id, amount)
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'error')"""
)

# 5. Quotes
content = re.sub(
    r"""        # Obtener precio base real
        product_data = APIClient\.get_product\(service_id\)
        base_price = product_data\.get\('price', 12000\) if product_data else 12000
        
        # Aplicar multiplicadores
        size_mult = \{"sedan": 1\.0, "suv": 1\.3, "pickup": 1\.5, "moto": 0\.6\}\.get\(size, 1\.0\)
        dirt_mult = \{"leve": 1\.0, "moderada": 1\.2, "extrema": 1\.6\}\.get\(dirt, 1\.0\)
        total_price = base_price \* size_mult \* dirt_mult
        
        # Enriquecer comentarios con metadatos del estimador
        full_comments = f"\[\{size\.upper\(\)\} \/ Suciedad: \{dirt\.upper\(\)\}\] \{comments\}"
        
        APIClient\.create_quote\(\{
            "user_id": user_id,
            "service_id": service_id,
            "location": location,
            "comments": full_comments,
            "total_price": total_price
        \}\)
        flash\('¡Solicitud de cotización enviada con éxito!', 'success'\)""",
    """        success, msg = QuoteService.create_quote(user_id, service_id, location, comments, size, dirt)
        if success:
            flash(msg, 'success')
        else:
            flash(msg, 'error')""",
    content
)

content = content.replace(
    "quotes_data = APIClient.get_user_quotes(user_id)\n    user_quotes = [Quote(**q) for q in quotes_data]",
    "user_quotes = QuoteService.get_user_quotes(user_id)"
)

content = content.replace(
    "APIClient.pay_quote(",
    "QuoteService.pay_quote("
)

# 6. Reviews
content = content.replace(
    """        if not rating or not comment or not service_id:
            flash('Por favor, proporcione una calificación, un comentario y seleccione un servicio.', 'error')
        else:
            APIClient.create_review({
                "user_id": user_id,
                "service_id": service_id,
                "rating": int(rating),
                "comment": comment
            })
            flash('¡Reseña publicada con éxito!', 'success')""",
    """        success, msg = ProductService.create_review(user_id, service_id, rating, comment)
        if success:
            flash(msg, 'success')
        else:
            flash(msg, 'error')"""
)

content = content.replace(
    "reviews_data = APIClient.get_reviews()\n    all_reviews = [Review(**r) for r in reviews_data]",
    "all_reviews = ProductService.get_reviews()"
)

# 7. Wallet Transactions
content = content.replace(
    "all_transactions = APIClient.get_user_transactions(user.id)\n    user.transactions = [WalletTransaction(**t) for t in all_transactions if \"Pago\" in t.get('description', '')]",
    "user.transactions = UserService.get_user_transactions(user.id, filter_keyword=\"Pago\")"
)

# 8. Gallery
content = content.replace(
    "APIClient.get(f\"/vehicles/{vehicle_id}\")",
    "get_vehicle(vehicle_id)"
)

content = content.replace(
    """APIClient.post("/gallery", {
            "vehicle_id": vehicle_id,
            "image_path": f"static/uploads/gallery/{filename}"
        })""",
    """add_gallery_image(vehicle_id, f"static/uploads/gallery/{filename}")"""
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
