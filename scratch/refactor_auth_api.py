import os
import re

# FIX main.py pay_quote
file_main = r'c:\Users\joans\Downloads\AplicacionMovil\presentacion\rutas\main.py'
with open(file_main, 'r', encoding='utf-8') as f:
    content_main = f.read()

content_main = content_main.replace(
    """    result = QuoteService.pay_quote(quote_id, method=method)
    
    if result.get('success'):
        flash(result.get('message', '¡Pago realizado con éxito!'), 'success')
    else:
        current_uid = session.get('user_id')
        flash(f"Error al pagar (Sesión UID: {current_uid}): {result.get('error', 'Desconocido')}", 'error')""",
    """    success, msg = QuoteService.pay_quote(quote_id, method=method)
    if success:
        flash(msg, 'success')
    else:
        current_uid = session.get('user_id')
        flash(f"Error al pagar (Sesión UID: {current_uid}): {msg}", 'error')"""
)

with open(file_main, 'w', encoding='utf-8') as f:
    f.write(content_main)

# Refactor auth.py
file_auth = r'c:\Users\joans\Downloads\AplicacionMovil\presentacion\rutas\auth.py'
with open(file_auth, 'r', encoding='utf-8') as f:
    content_auth = f.read()

content_auth = content_auth.replace(
    "from persistencia.api_client import APIClient",
    "from negocio.audit_service import AuditService\nfrom negocio.user_service import UserService"
)

content_auth = content_auth.replace(
    "APIClient.log_audit(",
    "AuditService.log_audit("
)

content_auth = content_auth.replace(
    "APIClient.get_user_by_id(",
    "UserService.get_user_by_id("
)

content_auth = content_auth.replace(
    """localidades_data = APIClient.get("/localidades", params=params) or []""",
    """localidades_data = UserService.get_localidades(tipo=tipo, provincia=provincia, canton=canton)"""
)

content_auth = content_auth.replace(
    """    data = APIClient.get(f"/padron/{cedula}")
    if not data:
        return jsonify({"error": "No encontrado"}), 404
    return jsonify(data)""",
    """    data = UserService.get_padron(cedula)
    if not data:
        return jsonify({"error": "No encontrado"}), 404
    return jsonify(data)"""
)

# Fix user initialization
content_auth = re.sub(
    r"user_data = UserService\.get_user_by_id\((.*?)\)\s+user = User\(\*\*user_data\)",
    r"user = UserService.get_user_by_id(\1)",
    content_auth
)

# `APIClient.update_user` in `mfa_setup` - should be in user_service or auth_service. 
# We'll just leave APIClient import in auth_service if needed, but in auth.py we need to replace it.
# Actually I removed APIClient from auth.py. I need to make sure I add `update_user` somewhere.
# I'll just restore APIClient import in auth.py for update_user, get_vehicle_by_plate, get_recovery_token, use_recovery_token for now to keep it running.
content_auth = "from persistencia.api_client import APIClient\n" + content_auth

with open(file_auth, 'w', encoding='utf-8') as f:
    f.write(content_auth)

# Refactor api.py
file_api = r'c:\Users\joans\Downloads\AplicacionMovil\presentacion\rutas\api.py'
with open(file_api, 'r', encoding='utf-8') as f:
    content_api = f.read()

content_api = content_api.replace(
    "from persistencia.api_client import APIClient",
    "from negocio.product_service import ProductService\nfrom negocio.loyalty_service import LoyaltyService"
)

content_api = content_api.replace(
    """        product = APIClient.get_product(service_id)
        if product:
            base_price = product.get('price', base_price)""",
    """        product = ProductService.get_product(service_id)
        if product:
            base_price = getattr(product, 'price', base_price)"""
)

content_api = content_api.replace(
    """        history = APIClient.get(f"/user-history/{uid}")
        if not history: return jsonify({"error": "No se encontró historial"}), 404
        
        total_spent = sum(t['amount'] for t in history.get('billing', []))
        visit_count = len(history.get('services', []))
        
        tier = "BRONCE"
        if visit_count >= 10: tier = "PLATINO"
        elif visit_count >= 5: tier = "ORO"
        elif visit_count >= 2: tier = "PLATA"
        
        return jsonify({
            "estatus": tier,
            "visitas_registradas": visit_count,
            "beneficio_actual": f"{15 if tier == 'PLATINO' else 10 if tier == 'ORO' else 5 if tier == 'PLATA' else 0}% de descuento"
        })""",
    """        status_data, err = LoyaltyService.get_user_loyalty_status(uid)
        if err: return jsonify({"error": err}), 404
        return jsonify(status_data)"""
)

with open(file_api, 'w', encoding='utf-8') as f:
    f.write(content_api)

print("Done")
