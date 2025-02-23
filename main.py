from fastapi import FastAPI
import qrcode
import rsa
import base64
from cryptography.fernet import Fernet
from fastapi.responses import FileResponse
from pydantic import BaseModel
import io

app = FastAPI()

class QRRequest(BaseModel):
    data : str

class DecryptRequest(BaseModel):
    encrypted_data : str

# Generate encryption keys
public_key, private_key = rsa.newkeys(512)
fernet_key = Fernet.generate_key()
cipher_suite = Fernet(fernet_key)

def encrypt_data(data: str) -> str:
    """Encrypt data using RSA."""
    try:
        encrypted_data = rsa.encrypt(data.encode(), public_key)
        return base64.b64encode(encrypted_data).decode()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Encryption failed: " + str(e))

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt data using RSA."""
    try:
        decoded_data = base64.b64decode(encrypted_data)
        return rsa.decrypt(decoded_data, private_key).decode()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Decryption failed: " + str(e))

@app.get("/")
def home():
    return {"message": "QR Code API is Running!"}

@app.post("/generate_qr")
def generate_qr(request: QRRequest):
    """Encrypt data Generate QR code for the given data as base64."""
    encrypted_data = encrypt_data(request.data)
    qr = qrcode.make(encrypted_data)
    #file_path = "qr_code.png" # to be used later to download file
    # Save QR Code in memory instead of a file
    img_buffer = io.BytesIO()    
    qr.save(img_buffer, format="PNG") # this saves the file in server
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
    
    return {
        "message" : "QR Code generated successfully!",
        "encrypted_data" : encrypted_data,
        "qr_code_base64" : img_base64
    }

@app.post("/decrypt_qr")
def decrypt_qr(request: DecryptRequest):
    """Decrypt data from QR code."""
    try:
        decrypted = decrypt_data(request.encrypted_data)
        return {"decrypted_data": decrypted}
    except Exception as e:
        return {"error": f"Decryption failed {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
