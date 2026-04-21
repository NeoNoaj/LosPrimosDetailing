from persistencia.modelos import User, RecoveryToken
from persistencia.api_client import APIClient
from persistencia.extensiones import mail
from flask_mail import Message
import secrets
from datetime import datetime, timedelta
from negocio.security_utils import SecurityUtils
from flask import request

def authenticate_user(email, password):
    user_data = APIClient.get_user_by_email(email)
    if user_data:
        user = User(**user_data)
        if SecurityUtils.check_password(password, user.password):
            return user
    
    # Log failed attempt
    SecurityUtils.log_event(None, "FAILED_LOGIN", request.remote_addr, f"Email: {email}")
    return None

def create_recovery_token(email):
    user_data = APIClient.get_user_by_email(email)
    if user_data:
        user = User(**user_data)
        token = secrets.token_urlsafe(32)
        expiration = datetime.utcnow() + timedelta(hours=1)
        
        # Save to DB via API
        APIClient.create_recovery_token(user.id, token, expiration)
        
        SecurityUtils.log_event(user.id, "RECOVERY_REQUESTED", request.remote_addr)
        return token, user
    return None, None

def send_recovery_email(user, reset_link):
    msg = Message(
        subject="Password Recovery - LosPrimosApp",
        recipients=[user.email]
    )
    msg.body = f"Hello {user.name}, click here to reset your password: {reset_link}"
    msg.html = f"<h2>Password Recovery</h2><p>Hello {user.name},</p><p><a href='{reset_link}'>Reset password</a></p>"
    mail.send(msg)

def update_password(email, new_password):
    user_data = APIClient.get_user_by_email(email)
    if not user_data:
        return False, "Usuario no encontrado."
    
    user = User(**user_data)

    # Validate Policy
    is_valid, msg = SecurityUtils.validate_password_policy(new_password)
    if not is_valid:
        return False, msg

    if SecurityUtils.is_password_reused(user.id, new_password):
        return False, "La contraseña ya ha sido utilizada en los últimos 9 meses."

    hashed_pw = SecurityUtils.hash_password(new_password)
    
    # Update via API
    APIClient.update_user(user.id, {
        "password": hashed_pw,
        "password_changed_at": datetime.utcnow().isoformat()
    })
    
    # Add to history
    APIClient.add_password_history(user.id, hashed_pw)
    
    SecurityUtils.log_event(user.id, "PASSWORD_CHANGED", request.remote_addr)
    return True, "Contraseña actualizada con éxito."

def register_user(email, password, name, pais='Costa Rica', provincia=None, canton=None, distrito=None, cedula=None, codelec=None):
    existing_user = APIClient.get_user_by_email(email)
    if existing_user:
        return None, "Email already registered."
    
    is_valid, msg = SecurityUtils.validate_password_policy(password)
    if not is_valid:
        return None, msg

    try:
        hashed_pw = SecurityUtils.hash_password(password)
        resp = APIClient.create_user({
            "email": email, 
            "password": hashed_pw, 
            "name": name,
            "pais": pais,
            "provincia": provincia,
            "canton": canton,
            "distrito": distrito,
            "cedula": cedula,
            "codelec": codelec
        })
        
        if resp.get('success'):
            user_id = resp['id']
            # Add to history
            APIClient.add_password_history(user_id, hashed_pw)
            SecurityUtils.log_event(user_id, "USER_REGISTERED", request.remote_addr)
            return User(id=user_id, email=email, name=name), None
        else:
            return None, resp.get('error', 'Error in registration')
            
    except Exception as e:
        return None, f"An unexpected error occurred: {str(e)}"

def search_users(query):
    # This is a bit complex via API if not implemented specifically.
    # For now, let's list all and filter, or I should have added a search endpoint.
    # I added a helper to list all users, but search is better.
    # Let's list all users for now.
    users_data = APIClient.get("/users") or []
    users = [User(**u) for u in users_data]
    
    filtered = []
    q = query.lower()
    for u in users:
        if q in u.email.lower() or q in u.name.lower():
            filtered.append(u)
            
    # Also search by plate
    vehicle_data = APIClient.get(f"/vehicles/plate/{query}")
    if vehicle_data:
        owner_id = vehicle_data['user_id']
        owner_data = APIClient.get_user_by_id(owner_id)
        if owner_data:
            owner = User(**owner_data)
            if owner.id not in [u.id for u in filtered]:
                filtered.append(owner)
                
    return filtered

def admin_reset_password(user_id, new_password):
    user_data = APIClient.get_user_by_id(user_id)
    if not user_data:
        return False, "Usuario no encontrado."
    
    user = User(**user_data)

    is_valid, msg = SecurityUtils.validate_password_policy(new_password)
    if not is_valid:
        return False, msg

    hashed_pw = SecurityUtils.hash_password(new_password)
    
    APIClient.update_user(user.id, {
        "password": hashed_pw,
        "password_changed_at": datetime.utcnow().isoformat(),
        "mfa_enabled": False,
        "mfa_secret": None
    })
    
    APIClient.add_password_history(user.id, hashed_pw)
    
    return True, f"Contraseña restablecida y MFA desactivado para {user.email}"
