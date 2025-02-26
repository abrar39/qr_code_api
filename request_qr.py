import requests
import uuid

#int_id = 1
#product_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(int_id)))  # Convert integer to UUID
#print(product_id)

product_id = "67020042-ba4d-435e-af9c-2945978d1ead"

#url = "https://qr-code-api-a29l.onrender.com/generate_qr_supabase"
url = "http://localhost:8000/generate_qr_supabase"
data = {"id": product_id}
response = requests.post(url, json=data)

with open("downloaded_qr.png", "wb") as f:
    f.write(response.content)