from persistencia.api_client import APIClient
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from negocio.auth_service import authenticate_user, create_recovery_token, send_recovery_email, update_password, register_user
from negocio.mfa_service import MFAService
from negocio.security_utils import SecurityUtils
from persistencia.modelos import User, RecoveryToken, Localidad
from negocio.audit_service import AuditService
from negocio.user_service import UserService
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        pais = request.form.get('pais', 'Costa Rica')
        provincia = request.form.get('provincia')
        canton = request.form.get('canton')
        distrito = request.form.get('distrito')
        cedula = request.form.get('cedula')
        codelec = request.form.get('codelec')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('register.html', form_data=request.form)
        
        user, error = register_user(email, password, name, pais, provincia, canton, distrito, cedula, codelec)
        if user:
            flash('¡Registro exitoso! Por favor inicia sesión.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(error, 'error')
            return render_template('register.html', form_data=request.form)
            
    return render_template('register.html', form_data={})

@auth_bp.route('/api/localidades')
def api_localidades():
    tipo = request.args.get('tipo')
    provincia = request.args.get('provincia')
    canton = request.args.get('canton')
    
    params = {}
    if tipo: params['tipo'] = tipo
    if provincia: params['provincia'] = provincia
    if canton: params['canton'] = canton

    localidades_data = UserService.get_localidades(tipo=tipo, provincia=provincia, canton=canton)
    return jsonify(localidades_data)
@auth_bp.route('/api/padron/<cedula>')
def api_padron(cedula):
    data = UserService.get_padron(cedula)
    if not data:
        return jsonify({"error": "No encontrado"}), 404
    return jsonify(data)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = authenticate_user(email, password)
        if user:
            if user.mfa_enabled:
                session['mfa_user_id'] = user.id
                return redirect(url_for('auth.mfa_verify'))
            
            session['user_id'] = user.id
            AuditService.log_audit(user.id, "LOGIN_SUCCESS", request.remote_addr, "Login manual")
            return redirect(url_for('main.dashboard'))
        
        flash('Credenciales inválidas', 'error')
        AuditService.log_audit(None, "LOGIN_FAILED", request.remote_addr, f"Email: {email}")
    return render_template('login.html')

@auth_bp.route('/mfa/verify', methods=['GET', 'POST'])
def mfa_verify():
    if 'mfa_user_id' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        code = request.form['code']
        user = UserService.get_user_by_id(session['mfa_user_id'])
        
        secret = SecurityUtils.decrypt_data(user.mfa_secret)
        if not secret:
            flash('Error técnico con la llave de seguridad. Por favor contacta soporte.', 'error')
            AuditService.log_audit(user.id, "MFA_DECRYPT_FAILED", request.remote_addr, "")
            return redirect(url_for('auth.login'))

        if MFAService.verify_totp(secret, code):
            session['user_id'] = user.id
            session.pop('mfa_user_id', None)
            AuditService.log_audit(user.id, "LOGIN_SUCCESS_MFA", request.remote_addr, "")
            return redirect(url_for('main.dashboard'))
        
        flash('Código MFA inválido', 'error')
        AuditService.log_audit(user.id, "MFA_VERIFY_FAILED", request.remote_addr, "")
        
    return render_template('mfa_verify.html')

@auth_bp.route('/mfa/setup', methods=['GET', 'POST'])
def mfa_setup():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = UserService.get_user_by_id(session['user_id'])
    
    if request.method == 'POST':
        code = request.form['code']
        secret = session.get('pending_mfa_secret')
        
        if MFAService.verify_totp(secret, code):
            APIClient.update_user(user.id, {
                "mfa_enabled": True,
                "mfa_secret": SecurityUtils.encrypt_data(secret)
            })
            session.pop('pending_mfa_secret', None)
            flash('MFA activado con éxito', 'success')
            AuditService.log_audit(user.id, "MFA_ENABLED", request.remote_addr, "")
            return redirect(url_for('main.dashboard'))
        
        flash('Código inválido. Intenta de nuevo.', 'error')

    secret = session.get('pending_mfa_secret')
    if not secret:
        secret = MFAService.generate_secret()
        session['pending_mfa_secret'] = secret
    
    totp_uri = MFAService.get_totp_uri(user.email, secret)
    qr_code = MFAService.generate_qr_code(totp_uri)
    
    return render_template('mfa_setup.html', qr_code=qr_code, secret=secret)

@auth_bp.route('/logout')
def logout():
    uid = session.get('user_id')
    if uid:
        AuditService.log_audit(uid, "LOGOUT", request.remote_addr, "")
    session.pop('user_id', None)
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        token, user = create_recovery_token(email)
        if user:
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            try:
                send_recovery_email(user, reset_link)
                flash('Se ha enviado un enlace de recuperación a tu correo.', 'success')
            except Exception as e:
                flash('Error al enviar el correo. Por favor intenta de nuevo más tarde.', 'error')
        else:
            flash('Si el correo está registrado, recibirás un enlace de recuperación.', 'info')
        return redirect(url_for('auth.forgot_password'))
    return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    recovery_data = APIClient.get_recovery_token(token)
    if not recovery_data or recovery_data.get('used'):
        flash('El enlace es inválido o ya ha sido utilizado.', 'error')
        return redirect(url_for('auth.forgot_password'))

    # API returns ISO strings, need to parse for comparison
    expires_at = datetime.fromisoformat(recovery_data['expires_at'].replace('Z', ''))
    if datetime.utcnow() > expires_at:
        flash('El enlace ha expirado.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    user = UserService.get_user_by_id(recovery_data['user_id'])
    
    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']
        if new_password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('reset_password.html', token=token)
        
        success, msg = update_password(user.email, new_password)
        if success:
            APIClient.use_recovery_token(token)
            flash(msg, 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(msg, 'error')
    
    return render_template('reset_password.html', token=token)

@auth_bp.route('/forgot-email', methods=['GET', 'POST'])
def forgot_email():
    if request.method == 'POST':
        name = request.form['name']
        plate = request.form['plate']
        vehicle_data = APIClient.get_vehicle_by_plate(plate)
        if vehicle_data:
            owner_data = UserService.get_user_by_id(vehicle_data['user_id'])
            if owner_data and owner_data['name'].lower() == name.lower():
                email = owner_data['email']
                parts = email.split('@')
                masked = parts[0][0] + "***@" + parts[1]
                flash(f'Tu cuenta está asociada al correo: {masked}', 'info')
                return render_template('forgot_email.html')
        
        flash('No se encontró ninguna cuenta con esos datos.', 'error')
    return render_template('forgot_email.html')

@auth_bp.route('/admin/recover-user', methods=['GET', 'POST'])
def admin_recover_user():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    admin_data = UserService.get_user_by_id(session['user_id'])
    if not admin_data or not admin_data.get('is_admin'):
        flash('Acceso denegado. Se requieren permisos de administrador.', 'error')
        return redirect(url_for('main.dashboard'))
    
    users = []
    if request.method == 'POST':
        if 'query' in request.form:
            from negocio.auth_service import search_users
            users = search_users(request.form['query'])
        elif 'user_id' in request.form:
            from negocio.auth_service import admin_reset_password
            user_id = request.form['user_id']
            new_pass = request.form['new_password']
            success, msg = admin_reset_password(user_id, new_pass)
            if success:
                flash(msg, 'success')
                AuditService.log_audit(admin_data['id'], f"ADMIN_RESET_PWD_USER_{user_id}", request.remote_addr, "")
            else:
                flash(msg, 'error')
                
    return render_template('admin_recover_user.html', users=users)
