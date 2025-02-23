from fastapi import FastAPI
import qrcode
import rsa
import base64
from cryptography.fernet import Fernet

app = FastAPI()

# Generate encryption keys
public_key, private_key = rsa.newkeys(512)
fernet_key = Fernet.generate_key()
cipher_suite = Fernet(fernet_key)

def encrypt_data(data: str) -> str:
    """Encrypt data using RSA."""
    encrypted_data = rsa.encrypt(data.encode(), public_key)
    return base64.b64encode(encrypted_data).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt data using RSA."""
    decoded_data = base64.b64decode(encrypted_data)
    return rsa.decrypt(decoded_data, private_key).decode()

@app.get("/")
def home():
    return {"message": "QR Code API is Running!"}

@app.post("/generate_qr")
def generate_qr(data: str):
    encrypted_data = encrypt_data(data)
    qr = qrcode.make(encrypted_data)
    qr.save("qr_code.png")
    return {"message": "QR code generated successfully", "encrypted_data": encrypted_data}

@app.post("/decrypt_qr")
def decrypt_qr(encrypted_data: str):
    try:
        decrypted = decrypt_data(encrypted_data)
        return {"decrypted_data": decrypted}
    except:
        return {"error": "Decryption failed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
