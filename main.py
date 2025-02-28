from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import qrcode
import rsa
import base64
import os
import io
from cryptography.fernet import Fernet
from fastapi.responses import FileResponse
from pydantic import BaseModel
from supabase import create_client, Client

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update to match frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase
SUPABASE_URL = "https://eysobfootyncwukoixym.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV5c29iZm9vdHluY3d1a29peHltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAzMDU3MzksImV4cCI6MjA1NTg4MTczOX0.-bxSZXmE71aYQ3FkMJUJuoWorc6Iar28TI12vXj2pTw"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define Request Models
class ProductRequest(BaseModel):
    name: str
    description: str
    serial_number: str

class QRRequest(BaseModel):
    id: str  # UUID of the product

class DecryptRequest(BaseModel):
    encrypted_data: str

# File paths for RSA keys
PUBLIC_KEY_FILE = "public.pem"
PRIVATE_KEY_FILE = "private.pem"

# Generate or Load RSA Keys
def generate_keys():
    """Generate a new RSA key pair and save them if they don't exist."""
    if not (os.path.exists(PUBLIC_KEY_FILE) and os.path.exists(PRIVATE_KEY_FILE)):
        public_key, private_key = rsa.newkeys(512)
        with open(PUBLIC_KEY_FILE, "wb") as pub_file:
            pub_file.write(public_key.save_pkcs1("PEM"))
        with open(PRIVATE_KEY_FILE, "wb") as priv_file:
            priv_file.write(private_key.save_pkcs1("PEM"))
    else:
        with open(PUBLIC_KEY_FILE, "rb") as pub_file:
            public_key = rsa.PublicKey.load_pkcs1(pub_file.read())
        with open(PRIVATE_KEY_FILE, "rb") as priv_file:
            private_key = rsa.PrivateKey.load_pkcs1(priv_file.read())
    
    return public_key, private_key

public_key, private_key = generate_keys()

def encrypt_data(data: str) -> str:
    """Encrypt data using RSA public key."""
    try:
        encrypted_data = rsa.encrypt(data.encode(), public_key)
        return base64.b64encode(encrypted_data).decode()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Encryption failed: {str(e)}")

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt data using RSA private key."""
    try:
        decoded_data = base64.b64decode(encrypted_data)
        return rsa.decrypt(decoded_data, private_key).decode()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decryption failed: {str(e)}")

@app.get("/")
def home():
    return {"message": "QR Code API is Running!"}

@app.get("/products")
def get_products():
    response = supabase.table("products").select("*").execute()
    return response.data

@app.post("/add_product")
def add_product(request: ProductRequest):
    """Insert a new product into Supabase."""
    response = supabase.table("products").insert({
        "name": request.name,
        "description": request.description,
        "serial_number": request.serial_number
    }).execute()

    if response.data:
        return {"message": "Product added successfully", "product": response.data[0]}
    else:
        raise HTTPException(status_code=500, detail="Failed to add product")

@app.post("/generate_qr")
def generate_qr(request: QRRequest):
    """Fetch product details from Supabase, encrypt, and generate a QR code."""
    response = supabase.table("products").select("*").eq("id", request.id).single().execute()
    
    if response.data is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product_data = response.data
    product_info = f"Name: {product_data['name']}, SN: {product_data['serial_number']}"
    encrypted_data = encrypt_data(product_info)

    # Generate QR Code
    img_buffer = io.BytesIO()
    qr = qrcode.make(encrypted_data)
    qr.save(img_buffer, format="PNG")

    # Return QR as base64 string
    return {
        "message": "QR Code generated successfully!",
        "encrypted_data": encrypted_data,
        "qr_code_base64": base64.b64encode(img_buffer.getvalue()).decode("utf-8")
    }

@app.post("/decrypt_qr")
def decrypt_qr(request: DecryptRequest):
    """Decrypt QR code data."""
    try:
        decrypted = decrypt_data(request.encrypted_data)
        return {"decrypted_data": decrypted}
    except Exception as e:
        return {"error": f"Decryption failed: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
