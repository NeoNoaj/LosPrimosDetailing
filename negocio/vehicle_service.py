from persistencia.modelos import Vehicle
from persistencia.api_client import APIClient

def get_user_vehicles(user_id):
    vehicles_data = APIClient.get_user_vehicles(user_id)
    return [Vehicle(**v) for v in vehicles_data]

def register_vehicle(user, plate, brand, model):
    existing_vehicle = APIClient.get_vehicle_by_plate(plate)
    if existing_vehicle:
        raise ValueError("Ya existe un vehículo con esta placa.")
    
    resp = APIClient.create_vehicle({
        "plate": plate,
        "brand": brand,
        "model": model,
        "user_id": user.id
    })
    
    if resp.get('success'):
        return Vehicle(id=resp['id'], plate=plate, brand=brand, model=model, user_id=user.id)
    else:
        raise ValueError(resp.get('error', 'Error registrering vehicle'))
