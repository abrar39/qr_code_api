from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import qrcode
import qrcode.constants
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
    #signature: str

class ScanRequest(BaseModel):
    qr_code_id: str
    scanned_data: str
    #signature: str
    scanned_by: str
    #scan_status: str
    location: str = None

class DeleteRequest(BaseModel):
    ids: list[uuid.UUID] # Expect multiple serial numbers


# Define Ecnryption, Digital Signature, and Decryption Functions
def encrypt_data(data: str) -> str:
    """Encrypt data using RSA public key."""
    try:
        # The data is encoded to bytes before encryption because RSA requires bytes
        encrypted_data = rsa.encrypt(data.encode(), public_key)
        # The data is decoded using base64 to convert it to a string
        return base64.b64encode(encrypted_data).decode()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Encryption failed: {str(e)}")

def decrypt_data(encrypted_data: str) -> tuple:
    """Decrypt data using RSA private key."""
    try:
        # Decode base64
        decoded_data = base64.b64decode(encrypted_data)
        
        # Decrypt using RSA
        decrypted_data = rsa.decrypt(decoded_data, private_key).decode()

        return True, decrypted_data

    except (base64.binascii.Error, ValueError) as e:
        # base64 decoding or RSA decryption failed (invalid input, incorrect padding, etc.)
        raise HTTPException(status_code=400, detail="Invalid encrypted data format.")

    except rsa.DecryptionError:
        # Raised if decryption fails (wrong key, corrupted data, etc.)
        raise HTTPException(status_code=401, detail="Decryption failed due to incorrect key or corrupted data.")

    except Exception as e:
        # Catch any other unexpected error
        raise HTTPException(status_code=500, detail="An unexpected error occurred during decryption.")
    
def sign_data(data: str) -> str:
    """Sign data using RSA private key."""
    # A signature of the encoded (from string to bytes) data is generated
    # using the private key and SHA-256 Hashing Algorithm
    signature = rsa.sign(data.encode(), private_key, "SHA-256")
    # The signature is decoded to convert it to a string and 
    # base64 encoding is used to convert to safe (for printing) characters
    return base64.b64encode(signature).decode()

def verify_signature(data: str, signature: str) -> bool:
    """Verify the signature of the data."""
    try:
        decoded_signature = base64.b64decode(signature)
        rsa.verify(data.encode(), decoded_signature, public_key)
        
        return True
    except rsa.VerificationError:
        # Signatured don't match
        return False
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signature verification failed: {str(e)}")

def convert_qr_to_data_and_signature(qr_code: str) -> tuple:
    """Convert the QR code to data and signature."""
    try:
        # Check if the data is in desired format
        qr_code = qr_code.split("|")
        data = qr_code[0].strip().split(":")[1].strip()
        signature = qr_code[1].strip().split(":")[1].strip()
        return data, signature
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid QR Code: {str(e)}")


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
    """
    Fetch product details from Supabase, encrypt, sign, and generate a QR code. 
    Store the QR data in the database. Finally, return the QR code as a base64 string.
    """

    response = supabase.table("products").select("*").eq("id", request.id).single().execute()
    
    if response.data is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product_data = response.data
    
    # product_info = f"Name: {product_data['name']} | SN: {product_data['serial_number']}"
    product_info = f"{product_data['id']}"
    
    # Encrypt and Sign the product data
    encrypted_data = encrypt_data(product_info) # encrypt the product data
    digital_signature = sign_data(product_info) # generate digital signature for the encrypted data

    # Concatenate the data and digital signatures to create the QR code
    product_data_and_signature = f"data: {encrypted_data} | signature: {digital_signature}"

    # Store the QR data in DB
    qr_code_id = str(uuid.uuid4())
    
    # Generate QR Code Image
    img_buffer = io.BytesIO()

    qr = qrcode.QRCode(
        version=10, # controls the size
        error_correction=qrcode.constants.ERROR_CORRECT_H, # High error correction
        box_size=10, # size of each box in pixels
        border=4, # border size
    )
    qr.add_data(product_data_and_signature)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(img_buffer, format="PNG")
    qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")

    # Save the data into database
    try:
        # Insert the encrypted data and digital signatures into the qr_codes table
        response = supabase.table("qr_codes").insert({
            "id": qr_code_id,
            "product_id": product_data["id"],
            "encrypted_data": encrypted_data,
            "digital_signature": digital_signature,
            "created_at": str(datetime.datetime.now(datetime.timezone.utc)), 
            "qr_code": qr_code_base64
        }).execute()
    except Exception as e:
        return {"error": f"Failed to store QR data: {str(e)}"}

    # Return QR as base64 string
    return {
        "message": "QR Code generated successfully!",
        "qr_code_id": qr_code_id,
        "encrypted_data": encrypted_data,
        "digital_signature": digital_signature,
        "product_data_and_signature": product_data_and_signature,
        "qr_code_base64": qr_code_base64
    }


@app.post("/scan_qr")
def scan_qr(request: ScanRequest):
    """
    Scan the QR. Decrypt the data and verify the signature.
    Finally store the scan event in the database
    """
    
    # Record a scan event in the database.
    scan_event_id = str(uuid.uuid4())
    scan_time = str(datetime.datetime.now(datetime.timezone.utc))
    
    # Get QR data and signature from the response
    scanned_qr_data, signature = convert_qr_to_data_and_signature(request.scanned_data)
    
    # Decrypt the scanned data
    is_decryption_successful = False
    try:
        is_decryption_successful, decrypted_data = decrypt_data(scanned_qr_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decryption failed: {str(e)}")
    
    # Verify the signature
    try:
        is_valid = verify_signature(decrypted_data, signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signature verification failed: {str(e)}")

    qry_response = supabase.table("scans").insert({
        "id": scan_event_id,
        "qr_code_id": request.qr_code_id,
        "scan_time": scan_time,
        "scanned_by": request.scanned_by,
        "location": request.location,
        "scan_status": "valid" if is_valid and is_decryption_successful else "tampered"
    }).execute()
    
    return {
        #"qr_code_id": request.qr_code_id,      # required for debugging
        #"scanned_data": request.scanned_data,  # required for debugging
        #"scanned_by": request.scanned_by,      # required for debugging
        #"location": request.location,          # required for debugging
        #"decrypted_data": decrypted_data,      # required for debugging
        "signature_verified": is_valid,
        "decryption_successful": is_decryption_successful
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
