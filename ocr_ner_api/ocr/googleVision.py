import os
import io
from PIL import Image, ImageEnhance, ImageOps
import numpy as np
import re
from rapidfuzz import process, fuzz
from transformers import BertForTokenClassification, BertTokenizer
import torch
import openai
from flask import Flask, jsonify
from flask import send_file
from flask import render_template
import subprocess
import sys
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
from fastapi import Request
from config import AZURE_ENDPOINT, AZURE_API_KEY, OPENAI_API_KEY, DB_CONFIG
import mysql.connector
from io import BytesIO


# Get the directory where this script (googleVision.py) lives
current_dir = os.path.dirname(os.path.abspath(__file__))


app = FastAPI()

def get_image_from_db(user_id):
    """Fetches the image from the database for the given user_id."""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT image, image_type FROM user_tbl WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row and row[0]:
        return row[0], row[1] or "image/jpeg"
    else:
        return None, None

# Add CORS middleware to allow requests from your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Replace with your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Import the extract_drug_names function from app2.py
from app2 import extract_drug_names

# Set up your OpenAI API key
openai.api_key = OPENAI_API_KEY

# Load the fine-tuned model and tokenizer
model_path = "vincentmark/biobert-ner"
model = BertForTokenClassification.from_pretrained(model_path)
tokenizer = BertTokenizer.from_pretrained(model_path)

# Function to get the path of a local image in the same folder
@app.post("/process-image")
async def process_image(request: Request):
    data = await request.json()
    print(f"Received data: {data}")
    
    user_id = data.get("user_id")

    if not user_id:
        return JSONResponse(content={"error": "No user_id provided"}, status_code=400)
    print(f"Processing image for user_id: {user_id}")

    temp_image_path = None

    try:
        image_data, image_type = get_image_from_db(user_id)
        if not image_data:
            return JSONResponse(content={"error": "Image not found in database"}, status_code=404)
       
        image = Image.open(BytesIO(image_data))
        temp_image_path = f"temp_image_{user_id}.jpg"
        image.save(temp_image_path)
        print(f"Image saved to {temp_image_path}")
        
        

        # Process the image
        raw_text, corrected_text, formatted_text, extracted_medicine_names = detect_text_in_image(temp_image_path)


        return JSONResponse(content={
            "raw_text": raw_text,
            "corrected_text": corrected_text,
            "formatted_text": formatted_text,
            "medicineArray": extracted_medicine_names
        
        
        })
    

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return JSONResponse(content={"error": f"Error processing the image: {str(e)}"}, status_code=500)
    finally:
        # Ensure the temporary image file is deleted
        if temp_image_path and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
            print(f"Temporary image file {temp_image_path} deleted.")


# Function to preprocess the image for better OCR accuracy
def preprocess_image(temp_image_path):
    """Preprocesses the image to enhance OCR accuracy."""
    image = Image.open(temp_image_path)
    image = image.convert("L")  # Convert to grayscale
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)  # Enhance contrast
    image_array = np.array(image)
    threshold = 128
    image_array = (image_array > threshold) * 255  # Apply binary thresholding
    image = Image.fromarray(image_array.astype("uint8"))
    image = ImageOps.expand(image, border=10, fill="white")  # Add white border
    image = image.convert("RGB")  # Convert back to RGB
    return image

# List of words to filter out
words_to_filter = [
    "NAME", "SEX", "AGE", "DATE", "ONCE", "EVERY", "HOURS", "HOUR", "DAY", "DAYS", "RX", "ADDRESS", "CITY", "SIGNATURE",
    "SIG", "LICENSE", "CARE", "PHYSICIAN", "PHYSICIAN'S", "DOCTOR", "DOCTOR'S", "POOR", "POUR", "APPLY", "WOUNDS", "WOUND",
    "INFECTION", "INFECTIONS", "THEN", "MAXICARE", "PHILHEALTH", "TIMES", "TWICE", "THRICE", "MEAL", "MEALS", "DAILY", "MONDAY",
    "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY", "MORNING", "AFTERNOON", "EVENING", "NIGHT", "MEDICAL",
    "CENTER", "CLINIC", "HOSPITAL", "PHARMACY", "PHARMACIST", "PHARMACIST'S", "PRESCRIPTION", "PRESCRIBE", "PRESCRIBED", "BEDTIME",
    "BREAKFAST", "LUNCH", "DINNER", "MG", "ML", "TAB", "CAP", "PM", "AM", "TABLET", "TABLETS", "CAPSULE", "CAPSULES", "DOSE",
    "DOSAGE", "DOSES", "DOSAGES", "DROPS", "PRINTED", "PRINT", "SIGN", "AND", "AREA", "NECK", "ARM", "LEG", "FOOT", "HAND", "WEEK",
    "FINGER", "TOE", "EYE", "EAR", "NOSE", "MOUTH", "THROAT", "STOMACH", "BACK", "CHEST", "SHOULDER", "KNEE", "ANKLE", "WRIST", "ARMS", "LEGS",
    "FEET", "HANDS", "FINGERS", "TOES", "EYES", "EARS", "NOSES", "MOUTHS", "THROATS", "STOMACHS", "BACKS", "CHESTS", "SHOULDERS", "KNEES",
]

# Words that will cause the entire line to be removed
line_removal_words = ["AGE", "NAME", "ADDRESS", "CITY", "CLINIC", "HOSPITAL", "PHARMACY", "PHYSICIAN", "DOCTOR", "SIGNATURE",]

# Load the FDA dictionary
# Build absolute path to FDA_dictionary.txt
drug_dictionary_path = os.path.join(current_dir, 'FDA_dictionary.txt')

with open(drug_dictionary_path, 'r', encoding='utf-8') as f:
    dictionary_terms = [line.strip() for line in f]

# Custom scorer combining multiple RapidFuzz scoring methods
def combined_scorer(term1, term2, **kwargs):
    """Combines multiple scoring methods from RapidFuzz."""
    ratio_score = fuzz.ratio(term1, term2)
    partial_ratio_score = fuzz.partial_ratio(term1, term2)
    token_sort_score = fuzz.token_sort_ratio(term1, term2)
    token_set_score = fuzz.token_set_ratio(term1, term2)

    combined_score = (
        0.4 * ratio_score +
        0.3 * partial_ratio_score +
        0.2 * token_sort_score +
        0.1 * token_set_score
    )
    return combined_score

# Function to get the best match using RapidFuzz
def get_best_match(input_term, dictionary_terms, scorer=combined_scorer, threshold=80):
    """Finds the best match for a term in the dictionary using RapidFuzz."""
    best_match = process.extractOne(input_term, dictionary_terms, scorer=scorer)
    if best_match and best_match[1] >= threshold:
        return best_match[0]  # Return the best match if the score is above the threshold
    return None  # Return None if no match meets the threshold

# Function to filter words in lines based on words_to_filter and remove lines with specific words
def filter_words_in_lines(lines, words_to_filter, line_removal_words):
    """Filters out specific words in each line and removes lines containing certain words."""
    filtered_lines = []
    for line in lines:
        # Remove the line if it contains any word in line_removal_words
        if any(removal_word.upper() in line.upper() for removal_word in line_removal_words):
            continue

        # Split the line into words and remove words in words_to_filter or words with 3 or fewer characters
        filtered_line = " ".join(
            word for word in line.split()
            if word.upper() not in words_to_filter and len(word) > 3
        )

        # Add the line to the result if it's not empty
        if filtered_line.strip():
            filtered_lines.append(filtered_line)
    return filtered_lines

# Function to call Azure Computer Vision API (latest version)
def call_azure_vision_api(temp_image_path):
    """Calls Azure Computer Vision API to extract text and captions from an image."""
    with open(temp_image_path, "rb") as image_file:
        image_data = image_file.read()

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_API_KEY,
        "Content-Type": "application/octet-stream",
    }
    params = {
        "features": "caption,read",  # Request both caption and OCR features
        "model-version": "latest",  # Use the latest model version
        "language": "en",           # Specify the language
        "api-version": "2024-02-01" # Use the latest API version
    }
    response = requests.post(
        f"{AZURE_ENDPOINT}/computervision/imageanalysis:analyze",  # Updated endpoint
        headers=headers,
        params=params,
        data=image_data,
    )
    response.raise_for_status()
    return response.json()

def detect_text_in_image(image_path):
    """Detects text in an image file using Azure Computer Vision, removes special characters and numbers, and applies RapidFuzz corrections."""
    # Preprocess the image
    preprocessed_image = preprocess_image(image_path)

    # Save the preprocessed image to a temporary file
    temp_image_path = "temp_preprocessed_image.jpg"
    preprocessed_image.save(temp_image_path)

    # Call Azure Computer Vision API
    ocr_result = call_azure_vision_api(temp_image_path)

    # Extract raw text from the OCR result
    raw_text = "\n".join(
        line.get("text", "") for block in ocr_result.get("readResult", {}).get("blocks", [])
        for line in block.get("lines", [])
    )

    # Print the raw extracted text
    print("\nRaw Extracted Text (Preserving Line Structure):")
    print(raw_text)

    # Remove special characters and numbers from the raw text
    text_without_special_chars = re.sub(r'[^a-zA-Z\s]', '', raw_text)

    # Split the cleaned text into lines
    lines = text_without_special_chars.splitlines()

    # Apply filtering to remove specific words in each line and remove lines with specific words
    filtered_lines = filter_words_in_lines(lines, words_to_filter, line_removal_words)

    # **Step 1: RapidFuzz Matching for Each Line**
    corrected_lines = []
    for line in filtered_lines:
        best_match = get_best_match(line, dictionary_terms)
        if best_match:
            if line != best_match:
                print(f"Line corrected: '{line}' -> '{best_match}'")  # Log line-level corrections
            corrected_lines.append(best_match)  # Use the line-level correction if a match is found
        else:
            # **Step 2: Fall Back to Word-Level RapidFuzz Matching**
            corrected_line = []
            for word in line.split():
                best_word_match = get_best_match(word, dictionary_terms)
                if best_word_match and word != best_word_match:
                    print(f"Word corrected: '{word}' -> '{best_word_match}'")  # Log word-level corrections
                    corrected_line.append(best_word_match)  # Use the word-level correction
                else:
                    corrected_line.append(word)  # Keep the original word if no match is found
            corrected_lines.append(" ".join(corrected_line))  # Reconstruct the corrected line

    # Combine the corrected lines back into a single string
    corrected_text = "\n".join(corrected_lines)

    print("\nCorrected Text (Line-Level with Word-Level Fallback):")
    print(corrected_text)

    # Format the corrected text using OpenAI
    formatted_text = format_corrected_text_with_openai(corrected_text)
    print("\nFormatted Text:")
    print(formatted_text)

        # Extract medicine names from the formatted text
    extracted_medicine_names = extract_drug_names(formatted_text)
    print("\nExtracted Medicine Names:")
    print(extracted_medicine_names)

    return raw_text, corrected_text, formatted_text, extracted_medicine_names

def format_corrected_text_with_openai(corrected_text):
    """Formats the corrected text using OpenAI to generate structured sentences and removes duplicates."""
    corrected_text_cleaned = re.sub(r'\s+', ' ', corrected_text).strip()

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant that formats text into structured sentences."},
                {"role": "user", "content": (
                    "Format the following text into sentences like '{medicine name} was prescribed'. "
                    "Exclude any brand names or additional details. Only include the generic medicine names:\n"
                    f"{corrected_text_cleaned}"
                )}
            ]
        )
        formatted_text = response['choices'][0]['message']['content']

        # Remove duplicate sentences
        sentences = formatted_text.split('. ')
        unique_sentences = list(dict.fromkeys(sentences))
        deduplicated_text = '. '.join(unique_sentences).strip()

        return deduplicated_text
    except openai.error.OpenAIError as e:
        return f"Error: {str(e)}"

def save_extracted_medicines_to_json(extracted_medicine_names):
    """Save the extracted medicine names to a JSON file and notify the API server."""
    json_file_path = 'thesis-webpage/ocr/extracted_medicines.json'
    with open(json_file_path, 'w') as json_file:
        json.dump(extracted_medicine_names, json_file)

    # Notify the API server about the new extracted medicines
    try:
        response = requests.post("http://127.0.0.1:8001/process-image", json={"medicineArray": extracted_medicine_names})
        if response.status_code == 200:
            print("Successfully notified the API server.")
        else:
            print(f"Failed to notify the API server: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error notifying the API server: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)