from flask import Flask, redirect, url_for
from persistencia.extensiones import mail
from presentacion.rutas.auth import auth_bp
from presentacion.rutas.main import main_bp
from presentacion.rutas.api import api_bp
from persistencia.api_client import APIClient
from persistencia.modelos import Localidad, User, Product
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    
    app.secret_key = 'tu_clave_secreta_muy_segura_cambiala'

    # Mail Configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'joangamer2102yt@gmail.com' 
    app.config['MAIL_PASSWORD'] = 'sudvyxneibgmxbla'  
    app.config['MAIL_DEFAULT_SENDER'] = 'joanmauriciomora21@gmail.com'

    # Initialize Extensions
    mail.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # Seeding logic via API
    try:
        # Check if localidades exist
        if not APIClient.get_localidades(tipo='pais'):
            APIClient.post("/localidades", {"nombre": "Costa Rica", "tipo": "pais"})
            # Note: This is a simplified seeding. For a full migration, you'd do more.
            # But the user wanted the connection GONE from Python.
    except Exception as e:
        print(f"Seeding error: {e}")

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
