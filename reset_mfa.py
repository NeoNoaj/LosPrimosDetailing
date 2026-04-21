from app import create_app
from persistencia.modelos import User
from persistencia.extensiones import db
import sys

def reset_mfa(email):
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            user.mfa_enabled = False
            user.mfa_secret = None
            db.session.commit()
            print(f"MFA reset successfully for {email}")
        else:
            print(f"User with email {email} not found.")

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "usuario@ejemplo.com"
    reset_mfa(email)
