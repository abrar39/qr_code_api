# 🔐 QR Code Encryption & Verification API

A **FastAPI-based backend** for generating, encrypting, signing, and verifying **secure QR codes** linked to products stored in a **Supabase** database.
This project implements **RSA encryption**, **digital signatures**, and **secure scan logging** to ensure product authenticity and traceability.

---

## 🚀 Features

* **Product Management**

  * Add, view, and delete products from Supabase.
* **QR Code Generation**

  * Encrypts product data with RSA.
  * Generates a digital signature for authenticity.
  * Produces QR codes as base64-encoded images.
* **QR Code Scanning**

  * Decrypts QR data and verifies its signature.
  * Records scan events (with time, location, and user info) in Supabase.
* **Security**

  * End-to-end RSA encryption/decryption.
  * Digital signature verification.
  * Data integrity checks.

---

## 🧰 Tech Stack

| Component          | Technology                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------- |
| Backend Framework  | [FastAPI](https://fastapi.tiangolo.com/)                                                           |
| Database           | [Supabase](https://supabase.com/)                                                                  |
| Encryption         | [RSA](https://stuvel.eu/python-rsa/) + [Fernet (cryptography)](https://cryptography.io/en/latest/) |
| QR Code Generation | [qrcode](https://pypi.org/project/qrcode/)                                                         |
| Data Models        | [Pydantic](https://docs.pydantic.dev/)                                                             |
| Server             | [Uvicorn](https://www.uvicorn.org/)                                                                |

---

## 📦 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # On Linux/Mac
venv\Scripts\activate      # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root with the following values:

```ini
SUPABASE_URL=https://<your-supabase-url>.supabase.co
SUPABASE_KEY=<your-supabase-api-key>
ALLOWED_ORIGINS=http://localhost,http://localhost:5173,https://your-frontend.vercel.app
```

> ⚠️ **Never commit your Supabase keys directly in code.** Use environment variables instead.

---

## ▶️ Running the Server

Start the FastAPI server using Uvicorn:

```bash
uvicorn main:app --reload
```

The API will run by default at:

```
http://127.0.0.1:8000
```

---

## 🔗 API Endpoints

### 🏠 Root

**GET /**
Returns a simple message confirming the server is running.

---

### 📦 Product Endpoints

#### 1. Get All Products

**GET /products**

#### 2. Add Product

**POST /add_product**

```json
{
  "name": "Product Name",
  "description": "Product Description",
  "serial_number": "12345"
}
```

#### 3. Delete Products

**DELETE /delete_product**

```json
{
  "ids": ["uuid1", "uuid2"]
}
```

---

### 🧾 QR Code Endpoints

#### 1. Generate QR Code

**POST /generate_qr**

```json
{
  "id": "product-uuid"
}
```

**Response:**

* Encrypted data
* Digital signature
* Base64-encoded QR image

---

#### 2. Scan QR Code

**POST /scan_qr**

```json
{
  "qr_code_id": "uuid",
  "scanned_data": "data: <encrypted> | signature: <base64>",
  "scanned_by": "John Doe",
  "location": "Warehouse A"
}
```

**Response:**

```json
{
  "signature_verified": true,
  "decryption_successful": true
}
```

---

## 🧠 Security Overview

* **RSA Encryption (512-bit)** used for encrypting product identifiers.
* **Digital Signatures** created using SHA-256 hash and RSA private key.
* **QR Code Integrity** verified upon scanning (detects tampering).
* **Scan Logging** ensures auditability with timestamps and locations.

---

## 📂 Project Structure

```
.
├── main.py               # FastAPI application
├── public.pem            # RSA public key
├── private.pem           # RSA private key
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
└── .env                  # Environment variables (not committed)
```

---

## 🧪 Example Supabase Tables

### `products`

| Column        | Type      | Description          |
| ------------- | --------- | -------------------- |
| id            | UUID      | Unique identifier    |
| name          | Text      | Product name         |
| description   | Text      | Product description  |
| serial_number | Text      | Product serial       |
| created_at    | Timestamp | Record creation time |

### `qr_codes`

| Column            | Type      | Description           |
| ----------------- | --------- | --------------------- |
| id                | UUID      | QR Code ID            |
| product_id        | UUID      | Related product       |
| encrypted_data    | Text      | RSA encrypted payload |
| digital_signature | Text      | Base64 signature      |
| qr_code           | Text      | Base64 QR image       |
| created_at        | Timestamp | Creation time         |

### `scans`

| Column      | Type      | Description           |
| ----------- | --------- | --------------------- |
| id          | UUID      | Scan ID               |
| qr_code_id  | UUID      | QR reference          |
| scan_time   | Timestamp | When scanned          |
| scanned_by  | Text      | Who scanned           |
| location    | Text      | Where scanned         |
| scan_status | Text      | `valid` or `tampered` |

---

## 🧑‍💻 Development Notes

* RSA keys (`public.pem`, `private.pem`) are generated automatically if missing.
* Ensure **Supabase tables** are created before running.
* Frontend URL must be listed in `allow_origins` for CORS.

---

## 📜 License

This project is licensed under the **MIT License**.
Feel free to modify and distribute for educational or commercial use.

---

## 👨‍💻 Author

**Abrar Asghar**
Data Analyst • AI Developer
