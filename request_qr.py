import requests

url = "https://qr-code-api-a29l.onrender.com/generate_qr"
data = {"data": "Hello, World!"}

response = requests.post(url, json=data)

print(response.json())  
# Should return: {"message": "QR code generated successfully", "encrypted_data": "..."}