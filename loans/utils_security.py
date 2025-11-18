import random, string, io, hashlib, os
from reportlab.lib.utils import ImageReader
import qrcode

def generate_serial(prefix="QL"):
    digits = ''.join(random.choices(string.digits, k=6))
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    return f"{prefix}{digits}{letters}"  # total 11 chars

def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def make_qr_image(data, error_correction='M'):
    qr = qrcode.QRCode(version=2, error_correction=getattr(qrcode.constants, f'ERROR_CORRECT_{error_correction.upper()}'), box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)
