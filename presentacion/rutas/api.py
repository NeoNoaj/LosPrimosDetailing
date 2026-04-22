from flask import Blueprint, jsonify, request, session
import requests
import re
from negocio.external_services import ExternalServices
from negocio.product_service import ProductService
from negocio.loyalty_service import LoyaltyService
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# -------------------------------------------------------------------
# REQ 2: 5 SERVICIOS EXPUESTOS (LÓGICA FUNCIONAL)
# -------------------------------------------------------------------

@api_bp.route('/recommendation', methods=['GET'])
def get_detailing_recommendation():
    location = ExternalServices.get_user_location_info()
    weather = ExternalServices.get_weather_info(lat=location.get('lat', 9.93), lon=location.get('lon', -84.08))
    
    temp = weather.get('main', {}).get('temp', 25)
    main_weather = weather.get('weather', [{}])[0].get('main', 'Clear')
    
    if main_weather in ['Rain', 'Drizzle', 'Thunderstorm']:
        rec = "Protección de Vidrios y Cerámico Lite"
        reason = "Se detectan lluvias próximas; mantén la visibilidad y repele el agua."
    elif temp > 28:
        rec = "Encerado de Alta Resistencia (Carnauba)"
        reason = "Sol intenso detectado; protege la laca contra los rayos UV."
    else:
        rec = "Lavado Premium Exterior"
        reason = "Condiciones óptimas para un mantenimiento de brillo estándar."

    return jsonify({
        "recomendacion": rec,
        "clima_actual": f"{temp}°C - {main_weather}",
        "causa": reason,
        "ubicacion": location.get('city', 'Costa Rica')
    })

@api_bp.route('/pricing/estimate', methods=['POST'])
def get_service_estimate():
    data = request.get_json() or {}
    service_id = data.get('service_id')
    
    # Intentar obtener el precio real del producto
    base_price = 12000 # Default
    if service_id:
        product = ProductService.get_product(service_id)
        if product:
            base_price = getattr(product, 'price', base_price)
    
    size_mult = {"sedan": 1.0, "suv": 1.3, "pickup": 1.5, "moto": 0.6}.get(data.get('size'), 1.0)
    dirt_mult = {"leve": 1.0, "moderada": 1.2, "extrema": 1.6}.get(data.get('dirt_level'), 1.0)
    
    total = base_price * size_mult * dirt_mult
    
    return jsonify({
        "monto_estimado": round(total, 2),
        "base_usada": base_price,
        "moneda": "CRC",
        "detalles": {
            "factor_tamano": size_mult,
            "factor_suciedad": dirt_mult
        },
        "aviso": "Sujeto a inspección física en el local."
    })

@api_bp.route('/loyalty/status', methods=['GET'])
def get_user_loyalty():
    uid = session.get('user_id') or request.args.get('user_id')
    if not uid: return jsonify({"error": "No autorizado"}), 401
    
    try:
        # Llamada al API Client (que ya llama al Web Service de Node.js)
        status_data, err = LoyaltyService.get_user_loyalty_status(uid)
        if err: return jsonify({"error": err}), 404
        return jsonify(status_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/tools/currency-convert', methods=['POST'])
def convert_prices():
    data = request.get_json() or {}
    amount_crc = data.get('monto_crc', 0)
    
    rate_info = ExternalServices.get_bccr_exchange_rate()
    sell_rate = rate_info.get('venta', 525.0)
    
    return jsonify({
        "monto_original_crc": amount_crc,
        "tipo_cambio": sell_rate,
        "monto_usd": round(amount_crc / sell_rate, 2),
        "api_fuente": rate_info.get('status', 'BCCR-SDDE')
    })

@api_bp.route('/security/identity-check', methods=['POST'])
def check_id_format():
    data = request.get_json() or {}
    cedula = str(data.get('cedula', ''))
    
    regex = r'^[1-9]-\d{4}-\d{4}$'
    is_valid = bool(re.match(regex, cedula))
    
    provincias = {
        "1": "San José", "2": "Alajuela", "3": "Cartago", 
        "4": "Heredia", "5": "Guanacaste", "6": "Puntarenas", 
        "7": "Limón", "8": "Extranjero", "9": "Casos Especiales"
    }
    
    prov_code = cedula[0] if is_valid else "0"
    
    return jsonify({
        "formato_valido": is_valid,
        "provincia_emision": provincias.get(prov_code, "Invalida"),
        "timestamp": datetime.now().isoformat()
    })

# --- NUEVOS SERVICIOS (REQ 2: EXPANSIÓN) ---

@api_bp.route('/tools/water-saving', methods=['POST'])
def calculate_water_saving():
    data = request.get_json() or {}
    washes = data.get('washes_count', 1)
    
    # Valores promedio: Home=250L, Pro=50L
    home_usage = 250 * washes
    pro_usage = 50 * washes
    saved = home_usage - pro_usage
    
    return jsonify({
        "ahorro_litros": saved,
        "equivalencia": f"Equivale a {round(saved / 20, 1)} garrafones de agua",
        "mensaje": "¡Gracias por ayudar al medio ambiente con un lavado profesional!"
    })

@api_bp.route('/vehicle/maintenance-predictor', methods=['POST'])
def predict_maintenance():
    data = request.get_json() or {}
    last_wash = data.get('last_wash_days', 7)
    color = data.get('car_color', 'white').lower()
    
    # Lógica base: colores oscuros necesitan más lavado
    days_to_next = 15
    if color in ['black', 'dark-blue', 'gray']:
        days_to_next = 10
        reason = "Los colores oscuros muestran el polvo y las manchas químicas más rápido."
    else:
        reason = "Tu color soporta bien la suciedad ligera, pero recomendamos mantenimiento cada 2 semanas."
        
    remaining = days_to_next - last_wash
    urgent = remaining <= 3
    
    return jsonify({
        "dias_recomendados_ciclo": days_to_next,
        "dias_restantes": max(0, remaining),
        "es_urgente": urgent,
        "recomendacion": "RESERVAR AHORA" if urgent else "Mantenimiento al día",
        "causa": reason
    })

@api_bp.route('/service/wait-time', methods=['GET'])
def get_wait_time():
    import random
    # Simulación de carga según la hora (más ocupado a mediodía)
    now = datetime.now()
    base_wait = 20 # mins
    
    if 11 <= now.hour <= 14:
        load = "ALTA"
        wait = base_wait + random.randint(30, 60)
    elif 17 <= now.hour <= 20:
        load = "MEDIA"
        wait = base_wait + random.randint(15, 30)
    else:
        load = "BAJA"
        wait = random.randint(10, 20)
        
    return jsonify({
        "carga_actual": load,
        "tiempo_espera_min": wait,
        "mensaje": f"Estimado de espera actual: {wait} minutos."
    })
