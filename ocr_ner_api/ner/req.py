import requests

url = "http://127.0.0.1:5000/extract-drugs" 
data = {"text": "Aspirin and Ibuprofen are commonly used drugs."}
headers = {"Content-Type": "application/json"}

try:
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()  # Raise an error for HTTP errors
    print(response.json())  # Attempt to parse JSON
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
except requests.exceptions.JSONDecodeError:
    print(f"Response is not valid JSON: {response.text}")