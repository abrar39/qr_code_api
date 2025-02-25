from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # to enable CORS for use with frontend
import qrcode
import rsa
import base64
from cryptography.fernet import Fernet
from fastapi.responses import FileResponse
from pydantic import BaseModel
from supabase import create_client, Client
import os

# Create the FAST API app
app = FastAPI()

# Update allowed origins to include frontend's Render URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # React local URL. Update this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase
SUPABASE_URL = "https://eysobfootyncwukoixym.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV5c29iZm9vdHluY3d1a29peHltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAzMDU3MzksImV4cCI6MjA1NTg4MTczOX0.-bxSZXmE71aYQ3FkMJUJuoWorc6Iar28TI12vXj2pTw"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class QRRequest(BaseModel):
    #data : str
    #id : int
    id : str    # to accept uuid

class DecryptRequest(BaseModel):
    encrypted_data : str

# Generate encryption keys
# File paths for saving the keys
PUBLIC_KEY_FILE = "public.pem"
PRIVATE_KEY_FILE = "private.pem"

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

# Load or generate keys
public_key, private_key = generate_keys()

#public_key, private_key = rsa.newkeys(512)
#fernet_key = Fernet.generate_key()
#cipher_suite = Fernet(fernet_key)

def encrypt_data(data: str) -> str:
    """Encrypt data using the stored public key."""
    try:
        encrypted_data = rsa.encrypt(data.encode(), public_key)
        return base64.b64encode(encrypted_data).decode()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Encryption failed: " + str(e))

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt data using stored private key."""
    try:
        decoded_data = base64.b64decode(encrypted_data)
        return rsa.decrypt(decoded_data, private_key).decode()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Decryption failed: " + str(e))

@app.get("/")
def home():
    return {"message": "QR Code API is Running!"}

@app.get("/products")
def get_products():
    response = supabase.table("products").select("*").execute()
    return response.data

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

@app.post("/generate_qr_supabase")
def generate_qr_supabase(request: QRRequest):
    # Fetch product data from Supabase
    response = supabase.table("products").select("*").eq("id", request.id).single().execute()
    if response.data is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product_data = response.data
    product_info = f"Name: {product_data['name']}, SN: {product_data['serial_number']}"

    encrypted_data = encrypt_data(product_info)
    file_path = f"qr_{request.id}.png"
    qr = qrcode.make(encrypted_data)
    qr.save(file_path)

    return FileResponse(file_path, media_type="image/png", filename=f"qr_{request.id}.png")

@app.post("/generate_qr/{product_id}")
def generate_qr(product_id: str):
    # Fetch product data from Supabase
    response = supabase.table("products").select("*").eq("id", product_id).single().execute()
    if response.data is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product_data = response.data
    product_info = f"Name: {product_data['name']}, SN: {product_data['serial_number']}"

    encrypted_data = encrypt_data(product_info)
    file_path = f"qr_{product_id}.png"
    qr = qrcode.make(encrypted_data)
    qr.save(file_path)

    return FileResponse(file_path, media_type="image/png", filename=f"qr_{product_id}.png")

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
