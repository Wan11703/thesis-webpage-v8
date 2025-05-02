import pandas as pd  # Import pandas for CSV handling
from flask import Flask, request, jsonify
from transformers import BertForTokenClassification, BertTokenizer
import torch
import os
import json

# Load medical_text from the JSON file
json_file_path = "c:/Users/Mark/OneDrive/Desktop/thesis-webpage/ocr/medical_text.json"
try:
    with open(json_file_path, "r") as json_file:
        medical_text = json.load(json_file)
    print("Loaded medical_text from JSON file.")
except FileNotFoundError:
    print(f"Error: {json_file_path} not found.")
    medical_text = []



 # Load the fine-tuned model and tokenizer
model_path = "c:/Users/Mark/OneDrive/Desktop/thesis-webpage/ner/ner_biobert/checkpoint-420"
model = BertForTokenClassification.from_pretrained(model_path)
tokenizer = BertTokenizer.from_pretrained(model_path)

# Function to extract drug names
def extract_drug_names(text):
     # Tokenize the input text
     inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)

     # Perform inference
     with torch.no_grad():
         outputs = model(**inputs)

     # Get predictions
     logits = outputs.logits
     predictions = torch.argmax(logits, dim=2)

     # Decode predictions
     tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
     labels = [model.config.id2label[p.item()] for p in predictions[0]]

     # Reconstruct words and their labels
     word_labels = []
     current_word = ""
     current_label = "O"

     for token, label in zip(tokens, labels):
         if token.startswith("##"):  # Subword token
             current_word += token[2:]  # Append subword without "##"
         else:
             if current_word:  # Save the previous word and its label
                 word_labels.append((current_word, current_label))
             current_word = token  # Start a new word
             current_label = label

     # Add the last word
     if current_word:
         word_labels.append((current_word, current_label))

     # Merge consecutive B-DRUG and I-DRUG tokens
     merged_drug_names = []
     current_drug = ""

     for word, label in word_labels:
         if label == "B-DRUG":
             if current_drug:  # Save the previous drug name
                 merged_drug_names.append(current_drug)
             current_drug = word  # Start a new drug name
         elif label == "I-DRUG":
             current_drug += word  # Append to the current drug name
         else:
             if current_drug:  # Save the previous drug name
                 merged_drug_names.append(current_drug)
                 current_drug = ""

     # Add the last drug name if any
     if current_drug:
         merged_drug_names.append(current_drug)

     return merged_drug_names



# Extract medicine names from the corrected field and store them in an array
medicine_names = []

for entry in medical_text:
    drug_name = entry.get('corrected', '')  # Get the corrected text
    merged_drug_names = extract_drug_names(drug_name)  # Extract drug names
    # Remove [SEP] tokens from the extracted drug names
    filtered_drug_names = [name.replace("[SEP]", "").strip() for name in merged_drug_names]
    medicine_names.extend(filtered_drug_names)  # Add the filtered drug names to the array

# Print the extracted medicine names
print("Extracted Medicine Names:", medicine_names)







