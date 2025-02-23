import requests

url = "https://qr-code-api-a29l.onrender.com/generate_qr"
data = {
    "data" : "Hello, FastAPI QR System!"
}

response = requests.post(url, json=data)
print(response.json())