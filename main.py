from fastapi import FastAPI
import qrcode
import rsa
import base64
from cryptography.fernet import Fernet
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

class QRRequest(BaseModel):
    data : str

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
def generate_qr(request: QRRequest):
    encrypted_data = encrypt_data(request.data)
    file_path = "qr_code.png" # to be used later to download file
    qr = qrcode.make(encrypted_data)
    qr.save(file_path) # this saves the file in server
    
    #return {"message": "QR code generated successfully", "encrypted_data": encrypted_data}
    return FileResponse(file_path, media_type="image/png", filename="qr_code.png")

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
