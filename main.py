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
import uuid
import datetime

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:5173",
    "https://qr-code-frontend-livid.vercel.app"
]

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Update to match frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase
SUPABASE_URL = "https://eysobfootyncwukoixym.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV5c29iZm9vdHluY3d1a29peHltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAzMDU3MzksImV4cCI6MjA1NTg4MTczOX0.-bxSZXmE71aYQ3FkMJUJuoWorc6Iar28TI12vXj2pTw"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


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

# Define Request PyDantic Models
class ProductRequest(BaseModel):
    name: str
    description: str
    serial_number: str

class QRRequest(BaseModel):
    id: str  # UUID of the product

class DecryptRequest(BaseModel):
    encrypted_data: str

class ScanRequest(BaseModel):
    qr_code_id: str
    scanned_by: str
    scan_status: str
    location: str

class DeleteRequest(BaseModel):
    ids: list[uuid.UUID] # Expect multiple serial numbers


# Define Ecnryption, Digital Signature, and Decryption Functions
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
    
def sign_data(data: str) -> str:
    """Sign data using RSA private key."""
    signature = rsa.sign(data.encode(), private_key, "SHA-256")
    return base64.b64encode(signature).decode()

def verify_signature(data: str, signature: str) -> bool:
    """Verify the signature of the data."""
    try:
        decoded_signature = base64.b64decode(signature)
        rsa.verify(data.encode(), decoded_signature, public_key)
        return True
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signature verification failed: {str(e)}")
        return False


# API ROUTES
@app.get("/")
def home():
    return {"message": "QR Code API is Running!"}

@app.get("/products")
def get_products():
    response = supabase.table("products").select("*").execute()
    return response.data

# UPDATE THIS
@app.post("/add_product")
def add_product(request: ProductRequest):
    """Insert a new product into Supabase."""
    response = supabase.table("products").insert({
        "id": str(uuid.uuid4()),
        "name": request.name,
        "description": request.description,
        "serial_number": request.serial_number, 
        "created_at": str(datetime.datetime.now(datetime.timezone.utc))
    }).execute()

    if response.data:
        return {"message": "Product added successfully", "product": response.data[0]}
    else:
        raise HTTPException(status_code=500, detail="Failed to add product")


@app.delete("/delete_product")
def delete_product(request: DeleteRequest):
    """Delete a product from Supabase."""
    # delete multiple products from supabase products table
    response = supabase.table("products").delete().in_("id", request.ids).execute()

    if response.data:
        return {"message": "Product deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete product")
    


@app.post("/generate_qr")
def generate_qr(request: QRRequest):
    """Fetch product details from Supabase, encrypt, and generate a QR code."""
    response = supabase.table("products").select("*").eq("id", request.id).single().execute()
    
    if response.data is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product_data = response.data
    product_info = f"Name: {product_data['name']}, SN: {product_data['serial_number']}"
    
    # Encrypt and Sign the product data
    encrypted_data = encrypt_data(product_info)
    digital_signature = sign_data(product_info)

    # Store the QR data in DB
    qr_code_id = str(uuid.uuid4())
    try:
        response = supabase.table("qr_codes").insert({
            "id": qr_code_id,
            "product_id": product_data["id"],
            "encrypted_data": encrypted_data,
            "digital_signature": digital_signature,
            "created_at": str(datetime.datetime.now(datetime.timezone.utc))
        }).execute()
    except Exception as e:
        return {"error": f"Failed to store QR data: {str(e)}"}
    # Generate QR Code Image
    img_buffer = io.BytesIO()
    qr = qrcode.make(encrypted_data)
    qr.save(img_buffer, format="PNG")

    # Return QR as base64 string
    return {
        "message": "QR Code generated successfully!",
        "qr_code_id": qr_code_id,
        "encrypted_data": encrypted_data,
        "digital_signature": digital_signature,
        "qr_code_base64": base64.b64encode(img_buffer.getvalue()).decode("utf-8")
    }

@app.post("/decrypt_qr")
def decrypt_qr(request: DecryptRequest):
    """Decrypt QR code data and Verify the Signature."""
    try:
        decrypted = decrypt_data(request.encrypted_data)
        signature_valid = verify_signature(decrypted, request.signature)
        return {"decrypted_data": decrypted, "signature_valid": signature_valid}

    except Exception as e:
        return {"error": f"Decryption failed: {str(e)}"}
    

@app.post("/scan_qr")
def scan_qr(request: ScanRequest):
    """Record a scan event in the database."""
    response = supabase.table("scans").insert({
        "id": str(uuid.uuid4()),
        "qr_code_id": request.qr_code_id,
        "scan_time": str(datetime.datetime.now(datetime.timezone.utc)),
        "scanned_by": request.scanned_by,
        "scan_status": request.scan_status,
        "location": request.location
    }).execute()

    if response.data:
        return {"message": "Scan event recorded successfully", "scan_event": response.data[0]}
    else:
        raise HTTPException(status_code=500, detail="Failed to record scan event")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
