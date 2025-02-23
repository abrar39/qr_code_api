import requests
import uuid

int_id = 1
product_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(int_id)))  # Convert integer to UUID
print(product_id)

url = "https://qr-code-api-a29l.onrender.com/generate_qr_supabase"
data = {"id": product_id}
response = requests.post(url, json=data)

with open("downloaded_qr.png", "wb") as f:
    f.write(response.content)