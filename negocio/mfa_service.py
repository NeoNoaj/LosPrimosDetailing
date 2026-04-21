import pyotp
import qrcode
import io
import base64
from negocio.security_utils import SecurityUtils

class MFAService:
    @staticmethod
    def generate_secret():
        return pyotp.random_base32()

    @staticmethod
    def get_totp_uri(email, secret):
        return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="LosPrimosDetailing")

    @staticmethod
    def generate_qr_code(totp_uri):
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    @staticmethod
    def verify_totp(secret, code):
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
