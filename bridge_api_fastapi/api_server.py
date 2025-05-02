from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
import os
import json
import asyncio
import requests

app = FastAPI()

# Add CORS middleware to allow requests from your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Replace with your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store the latest extracted medicines
latest_extracted_medicines = []

# Endpoint to serve extracted medicine names
@app.get("/api/extracted-medicines")
def get_extracted_medicines():
    json_file_path = 'C:/Users/Mark/OneDrive/Desktop/thesis-webpage/ocr/extracted_medicines.json'
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r') as file:
            extracted_medicines = json.load(file)
        return JSONResponse(content={"medicineArray": extracted_medicines})
    else:
        return JSONResponse(content={"medicineArray": []}, status_code=404)

# SSE endpoint to stream updates to the frontend
@app.get("/api/stream-medicines")
async def stream_medicines():
    async def event_generator():
        while True:
            # Stream the latest extracted medicines
            if latest_extracted_medicines:
                yield f"data: {json.dumps(latest_extracted_medicines)}\n\n"
            await asyncio.sleep(1)  # Check for updates every second

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Endpoint to update the latest extracted medicines
@app.post("/api/update-medicines")
async def update_medicines(request: Request):
    global latest_extracted_medicines
    data = await request.json()
    medicine_array = data.get("medicineArray")

    if medicine_array:
        latest_extracted_medicines = medicine_array
        print("Updated latest extracted medicines:", latest_extracted_medicines)
        return JSONResponse(content={"message": "Medicines updated successfully"})
    else:
        return JSONResponse(content={"error": "No medicines provided"}, status_code=400)



# Global variable to store the latest extracted medicines
latest_extracted_medicines = []

# Endpoint to process the image
@app.post("/api/process-image")
async def process_image(request: Request):
    data = await request.json()
    image_url = data.get("image_url")
    user_id = data.get("user_id")

    
    if not user_id:
        return JSONResponse(content={"error": "No user_id provided"}, status_code=403)

    # Use the proxy route on your Node server
    image_url = f"http://localhost:3000/api/image-proxy/{user_id}"



    try:
        # Forward the proxy URL to googleVision.py
        response = requests.post(
            "http://127.0.0.1:8001/process-image",
            json={"image_url": image_url, "user_id": user_id}
        )
        if response.status_code == 200:
            return JSONResponse(content=response.json())
        else:
            print("googleVision.py returned status:", response.status_code)
            print("googleVision.py response:", response.text)
            return JSONResponse(content={"error": "Failed to process the image in googleVision.py"}, status_code=500)
    except requests.exceptions.RequestException as e:
        return JSONResponse(content={"error": f"Error communicating with googleVision.py: {str(e)}"}, status_code=500)






if __name__ == "__main__":
    import uvicorn
    # Run the FastAPI app
    uvicorn.run(app, host="127.0.0.1", port=8000)