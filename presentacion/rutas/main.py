from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
from persistencia.modelos import User, Product, Review, Quote, GalleryImage, Vehicle, WalletTransaction
from persistencia.api_client import APIClient
from negocio.vehicle_service import get_user_vehicles, register_vehicle
from negocio.external_services import ExternalServices
from negocio.banking_service import BankingService
from datetime import datetime
import os
import requests
from werkzeug.utils import secure_filename

main_bp = Blueprint('main', __name__)

@main_bp.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_data = APIClient.get_user_by_id(session['user_id'])
        if user_data:
            user = User(**user_data)
            vehicles = get_user_vehicles(user.id)
            
            # [API CONSUMO 1 & 4] Ubicación y Clima
            location = ExternalServices.get_user_location_info()
            weather = ExternalServices.get_weather_info(city=location.get('city', 'San Jose'))
            
            # [API CONSUMO 3] Noticias Automotrices
            news = ExternalServices.get_automotive_news()
            
            return render_template('dashboard.html', 
                                 user=user, 
                                 vehicles=vehicles, 
                                 location=location,
                                 weather=weather,
                                 news=news,
                                 now=datetime.utcnow())
    return redirect(url_for('auth.login'))

@main_bp.route('/services')
def list_services():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    products_data = APIClient.get_products()
    products = [Product(**p) for p in products_data]
    
    # [API CONSUMO 5] Tipo de Cambio para conversión en UI
    rate = ExternalServices.get_bccr_exchange_rate()
    
    return render_template('services.html', products=products, exchange_rate=rate)

@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    product_data = APIClient.get_product(product_id)
    if not product_data:
        return "Producto no encontrado", 404
    product = Product(**product_data)
    return render_template('product_detail.html', product=product)

@main_bp.route('/wallet')
def wallet():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    user_data = APIClient.get_user_by_id(session['user_id'])
    user = User(**user_data)
    
    token_bccr = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJCQ0NSLVNEREUiLCJzdWIiOiJqb2FubWF1cmljaW9tb3JhMjFAZ21haWwuY29tIiwiYXVkIjoiU0RERS1TaXRpb0V4dGVybm8iLCJleHAiOjI1MzQwMjMwMDgwMCwibmJmIjoxNzc1NjAwNTcxLCJpYXQiOjE3NzU2MDA1NzEsImp0aSI6IjE0ZjNlNmE0LTMxNTMtNDcxOS04NGU1LWU0MzJlODc0NDE4OCIsImVtYWlsIjoiam9hbm1hdXJpY2lvbW9yYTIxQGdtYWlsLmNvbSJ9.Tw1pl5vCwWVzxGEc3YHH9twAKdy0KWXBrHeJiYFTcfc"
    rate = ExternalServices.get_bccr_exchange_rate(token_bccr)
    
    linked_card = BankingService.get_linked_card(user.id)
    bank_account = None
    bank_movements = []
    
    if linked_card:
        bank_account = BankingService.get_account_details(linked_card['bank_account_id'])
        if bank_account:
            all_bank_movements = BankingService.get_movements_by_account_id(bank_account['id'])
            # Filtrar: solo mostrar pagos por servicios (suelen contener la palabra "Pago")
            bank_movements = [m for m in all_bank_movements if "Pago" in m.get('detalle', '')]

    # También cargamos y filtramos transacciones de la wallet interna
    all_transactions = APIClient.get_user_transactions(user.id)
    user.transactions = [WalletTransaction(**t) for t in all_transactions if "Pago" in t.get('description', '')]


    return render_template('wallet.html', 
                         user=user, 
                         exchange_rate=rate,
                         linked_card=linked_card,
                         bank_account=bank_account,
                         bank_movements=bank_movements)

@main_bp.route('/wallet/unlink-card', methods=['POST'])
def wallet_unlink_card():
    if 'user_id' not in session: return jsonify({"error": "No autorizado"}), 401
    
    user_id = session['user_id']
    result = BankingService.unlink_card(user_id)
    
    if result.get('success'):
        flash('¡Tarjeta desvinculada con éxito!', 'success')
    else:
        flash(f'Error al desvincular: {result.get("error")}', 'error')
        
    return redirect(url_for('main.wallet'))


@main_bp.route('/wallet/link-card', methods=['POST'])
def wallet_link_card():
    if 'user_id' not in session: return jsonify({"error": "No autorizado"}), 401
    
    data = request.form
    user_id = session['user_id']
    
    result = BankingService.link_card(
        user_id,
        data.get('card_holder'),
        data.get('card_number'),
        data.get('cvv'),
        data.get('expiry_date')
    )
    
    if result.get('success'):
        flash('¡Tarjeta vinculada con éxito!', 'success')
    else:
        flash(f'Error: {result.get("error")}', 'error')
        
    return redirect(url_for('main.wallet'))

@main_bp.route('/api-health')
def api_health():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    uid = session['user_id']
    
    exposed = {
        "Currency-Convert": {"ok": False, "url": "/api/v1/tools/currency-convert"},
        "Identity-Check": {"ok": False, "url": "/api/v1/security/identity-check"},
        "Water-Saving": {"ok": False, "url": "/api/v1/tools/water-saving"},
        "Maint-Predictor": {"ok": False, "url": "/api/v1/vehicle/maintenance-predictor"},
        "Wait-Time": {"ok": False, "url": "/api/v1/service/wait-time"}
    }
    
    BASE_API = "http://127.0.0.1:5000/api/v1"
    try:
        if requests.get(f"{BASE_API}/recommendation").status_code == 200: exposed["Recommendation"]["ok"] = True
        if requests.get(f"{BASE_API}/loyalty/status?user_id={uid}").status_code == 200: exposed["Loyalty-Status"]["ok"] = True
        if requests.post(f"{BASE_API}/pricing/estimate", json={"size":"sedan"}).status_code == 200: exposed["Pricing-Estimate"]["ok"] = True
        if requests.post(f"{BASE_API}/tools/currency-convert", json={"monto_crc":10000}).status_code == 200: exposed["Currency-Convert"]["ok"] = True
        if requests.post(f"{BASE_API}/security/identity-check", json={"cedula":"1-2345-6789"}).status_code == 200: exposed["Identity-Check"]["ok"] = True
    except Exception as e:
        print(f"DEBUG: Health check error: {e}")

    consumed = [
        {"name": "BCCR (Exchange API)", "data": ExternalServices.get_bccr_exchange_rate(), "ok": True},
        {"name": "OpenWeather (Live Clima)", "data": ExternalServices.get_weather_info(), "ok": True},
        {"name": "NHTSA (Recalls Reales)", "data": ExternalServices.check_vehicle_recalls("Toyota", "Camry"), "ok": True},
        {"name": "IP-API (Geolocation)", "data": ExternalServices.get_user_location_info(), "ok": True},
        {"name": "NewsAPI (Car News)", "data": ExternalServices.get_automotive_news(), "ok": True},
        {"name": "DiceBear (User Avatars)", "data": {"status": "ONLINE", "url": "https://api.dicebear.com/7.x/avataaars/svg"}, "ok": True},
        {"name": "Sistema Bancario (Banco)", "data": {"status": "ONLINE" if BankingService.check_health()['bank'] else "OFFLINE"}, "ok": BankingService.check_health()['bank']},
        {"name": "Servicio de Persistencia (Local)", "data": {"status": "ONLINE" if BankingService.check_health()['local'] else "OFFLINE"}, "ok": BankingService.check_health()['local']}
    ]
    
    for api in consumed:
        if "error" in api["data"] or not api["data"]: api["ok"] = False

    user_data = APIClient.get_user_by_id(uid)
    user = User(**user_data) if user_data else None

    return render_template('api_health.html', user=user, exposed_status=exposed, consumed_status=consumed)

@main_bp.route('/wallet/recharge', methods=['POST'])
def wallet_recharge():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    user_data = APIClient.get_user_by_id(session['user_id'])
    user = User(**user_data)
    amount = request.form.get('amount', type=float)
    
    if amount and amount > 0:
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
        flash('Monto de recarga inválido.', 'error')
        
    return redirect(url_for('main.wallet'))

@main_bp.route('/vehicles', methods=['GET', 'POST'])
def vehicles():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    user_data = APIClient.get_user_by_id(session['user_id'])
    user = User(**user_data)
    
    if request.method == 'POST':
        plate = request.form['plate']
        brand = request.form['brand']
        model = request.form['model']
        try:
            register_vehicle(user, plate, brand, model)
            flash('Vehicle registered successfully', 'success')
            return redirect(url_for('main.vehicles'))
        except ValueError as e:
            flash(str(e), 'error')
            
    user_vehicles = get_user_vehicles(user.id)
    
    # [API CONSUMO 2] Enriquecer vehículos con datos de Recalls (NHTSA)
    for v in user_vehicles:
        # Hacemos la consulta para cada vehículo (en un entorno real esto se cachearía)
        recall_data = ExternalServices.check_vehicle_recalls(v.brand, v.model)
        v.recall_count = recall_data.get('Count', 0)
        v.recall_status = "ONLINE" if recall_data.get('status') == "ONLINE" else "OFFLINE"

    return render_template('vehicles.html', vehicles=user_vehicles, now=datetime.utcnow())

@main_bp.route('/quotes', methods=['GET', 'POST'])
def quotes():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    user_id = session['user_id']
    
    if request.method == 'POST':
        service_id = request.form['service_id']
        location = request.form['location']
        comments = request.form.get('comments', '')
        size = request.form.get('size', 'sedan')
        dirt = request.form.get('dirt', 'leve')
        
        # Obtener precio base real
        product_data = APIClient.get_product(service_id)
        base_price = product_data.get('price', 12000) if product_data else 12000
        
        # Aplicar multiplicadores
        size_mult = {"sedan": 1.0, "suv": 1.3, "pickup": 1.5, "moto": 0.6}.get(size, 1.0)
        dirt_mult = {"leve": 1.0, "moderada": 1.2, "extrema": 1.6}.get(dirt, 1.0)
        total_price = base_price * size_mult * dirt_mult
        
        # Enriquecer comentarios con metadatos del estimador
        full_comments = f"[{size.upper()} / Suciedad: {dirt.upper()}] {comments}"
        
        APIClient.create_quote({
            "user_id": user_id,
            "service_id": service_id,
            "location": location,
            "comments": full_comments,
            "total_price": total_price
        })
        flash('¡Solicitud de cotización enviada con éxito!', 'success')
        return redirect(url_for('main.quotes'))

    products_data = APIClient.get_products()
    services = [Product(**p) for p in products_data if p['category'] == 'service']
    
    quotes_data = APIClient.get_user_quotes(user_id)
    user_quotes = [Quote(**q) for q in quotes_data]
    
    from negocio.banking_service import BankingService
    has_card = BankingService.get_linked_card(user_id) is not None
    
    return render_template('quotes.html', services=services, quotes=user_quotes, has_card=has_card)

@main_bp.route('/quotes/pay/<int:quote_id>', methods=['POST'])
def pay_quote(quote_id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    
    method = request.form.get('method', 'wallet')
    result = APIClient.pay_quote(quote_id, method=method)
    
    if result.get('success'):
        flash(result.get('message', '¡Pago realizado con éxito!'), 'success')
    else:
        current_uid = session.get('user_id')
        flash(f"Error al pagar (Sesión UID: {current_uid}): {result.get('error', 'Desconocido')}", 'error')
        
    return redirect(url_for('main.quotes'))

@main_bp.route('/gallery')
def gallery():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    user_data = APIClient.get_user_by_id(session['user_id'])
    user = User(**user_data)
    return render_template('gallery.html', vehicles=user.vehicles)

@main_bp.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        user_id = session['user_id']
        service_id = request.form.get('service_id')
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        
        if not rating or not comment or not service_id:
            flash('Por favor, proporcione una calificación, un comentario y seleccione un servicio.', 'error')
        else:
            APIClient.create_review({
                "user_id": user_id,
                "service_id": service_id,
                "rating": int(rating),
                "comment": comment
            })
            flash('¡Reseña publicada con éxito!', 'success')
        return redirect(url_for('main.reviews'))

    reviews_data = APIClient.get_reviews()
    all_reviews = [Review(**r) for r in reviews_data]
    
    products_data = APIClient.get_products()
    services = [Product(**p) for p in products_data if p['category'] == 'service']
    
    return render_template('reviews.html', reviews=all_reviews, services=services)

@main_bp.route('/guides')
def guides():
    return render_template('guides.html')

@main_bp.route('/upload-gallery', methods=['POST'])
def upload_gallery():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    
    vehicle_id = request.form.get('vehicle_id')
    file = request.files.get('file')
    
    if not vehicle_id or not file:
        flash('Datos de subida incompletos.', 'error')
        return redirect(url_for('main.gallery'))
    
    vehicle_data = APIClient.get(f"/vehicles/{vehicle_id}")
    if not vehicle_data or vehicle_data['user_id'] != session['user_id']:
        flash('Vehículo no encontrado o no autorizado.', 'error')
        return redirect(url_for('main.gallery'))

    if file:
        filename = secure_filename(f"v{vehicle_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'gallery')
        
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
            
        file.save(os.path.join(upload_path, filename))
        
        APIClient.post("/gallery", {
            "vehicle_id": vehicle_id,
            "image_path": f"static/uploads/gallery/{filename}"
        })
        
        flash('¡Foto subida correctamente!', 'success')
        
    return redirect(url_for('main.gallery'))
