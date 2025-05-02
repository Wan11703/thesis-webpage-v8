import pandas as pd  # Import pandas for CSV handling
from flask import Flask, request, jsonify
from transformers import BertForTokenClassification, BertTokenizer
import torch
import os


current_dir = os.path.dirname(os.path.abspath(__file__))
# Initialize Flask app
app = Flask(__name__)

# Load the fine-tuned model and tokenizer
model_path = "vincentmark/biobert-ner"
model = BertForTokenClassification.from_pretrained(model_path)
tokenizer = BertTokenizer.from_pretrained(model_path)

# Load the FDA dictionary into a set for quick lookup
def load_known_drug_names(filepath):
    known_drug_names = set()
    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file:
            drug_name = line.strip().split('\t')[0].lower()  # Extract the drug name and convert to lowercase
            known_drug_names.add(drug_name)
    return known_drug_names

fda_dictionary_path = os.path.join(current_dir, 'FDA_dictionary.txt')
known_drug_names = load_known_drug_names(fda_dictionary_path)

# Define a list of irrelevant words to exclude
irrelevant_words = {"cream", "ointment", "suspension", "tablet", "capsule", "injection", "solution", "valerate", "and", "m.v.i. adult", ""}


def extract_drug_names(text):
    if len(text.split()) > 1024:
        raise ValueError("Input text is too long. Please split it into smaller chunks.")
    # Split text into manageable chunks
    chunk_size = 512  # Adjust based on your model's max token limit
    tokens = tokenizer(text, return_tensors="pt", truncation=False)["input_ids"][0]
    chunks = [tokens[i:i + chunk_size] for i in range(0, len(tokens), chunk_size)]

    merged_drug_names = []

    for chunk in chunks:
        # Convert chunk back to text
        chunk_text = tokenizer.decode(chunk, skip_special_tokens=True)

        # Tokenize the chunk
        inputs = tokenizer(chunk_text, return_tensors="pt", truncation=True, padding=True, max_length=512)

        # Perform inference
        with torch.no_grad():
            outputs = model(**inputs)

        # Get predictions and confidence scores
        logits = outputs.logits
        predictions = torch.argmax(logits, dim=2)
        scores = torch.softmax(logits, dim=2)  # Get probabilities for each token

        # Decode predictions
        tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        labels = [model.config.id2label[p.item()] for p in predictions[0]]
        confidences = [scores[0, i, p.item()].item() for i, p in enumerate(predictions[0])]

        # Reconstruct words and their labels
        word_labels = []
        current_word = ""
        current_label = "O"
        current_confidence = 0.0

        # Debugging: Print tokens, labels, and confidences
        print("Tokens, Labels, and Confidences:")
        for token, label, confidence in zip(tokens, labels, confidences):
            print(f"Token: {token}, Label: {label}, Confidence: {confidence}")
            if token.startswith("##"):  # Subword token
                current_word += token[2:]  # Append subword without "##"
                current_confidence = min(current_confidence, confidence)  # Use the lowest confidence in the word
            else:
                if current_word:  # Save the previous word and its label
                    if current_label.startswith("B-DRUG") or current_label.startswith("I-DRUG"):
                        if current_confidence > 0.2:  # Adjust threshold here
                            word_labels.append((current_word, current_label))
                current_word = token  # Start a new word
                current_label = label
                current_confidence = confidence

        # Add the last word
        if current_word and (current_label.startswith("B-DRUG") or current_label.startswith("I-DRUG")):
            if current_confidence > 0.2:  # Adjust threshold here
                word_labels.append((current_word, current_label))

        # Merge consecutive B-DRUG and I-DRUG tokens, allowing multi-word drugs
        current_drug = ""
        for word, label in word_labels:
            if label.startswith("B-DRUG") or label.startswith("I-DRUG"):
                if current_drug:  # Append space for multi-word drugs
                    current_drug += " "
                current_drug += word  # Add the current word to the drug name
            else:
                if current_drug:  # Save the previous drug name
                    merged_drug_names.append(current_drug)
                    current_drug = ""  # Reset for the next drug

        # Add the last drug name if any
        if current_drug:
            merged_drug_names.append(current_drug)

    # Post-processing: Check against known drug names
    final_drug_names = []
    for drug in merged_drug_names:
        if drug.lower() in known_drug_names:
            final_drug_names.append(drug)

    # Activate additional check only if not all medicines are identified
    if len(final_drug_names) < len(merged_drug_names):
        # Additional check: Match multi-word drugs directly from the text
        text_lower = text.lower()
        print("Additional Matching:")
        for known_drug in known_drug_names:
            if known_drug in text_lower:
                print(f"Matched: {known_drug}")
                final_drug_names.append(known_drug)

    # Remove duplicates
    final_drug_names = list(set(final_drug_names))

    # Sort by length (longer names first) to prioritize complete names
    final_drug_names = sorted(final_drug_names, key=len, reverse=True)

    # Remove partial or redundant names
    filtered_drug_names = []
    for i, drug in enumerate(final_drug_names):
        if not any(drug in other for j, other in enumerate(final_drug_names) if i != j):
            filtered_drug_names.append(drug)

    # Remove irrelevant words from the drug names
    cleaned_drug_names = []
    for drug in filtered_drug_names:
        cleaned_drug_names.append(" ".join([word for word in drug.split() if word.lower() not in irrelevant_words]))

    return cleaned_drug_names

corrected_text = "Rosuvastatin was prescribed. Aspirin was prescribed. Citicoline was prescribed. Baclofen was prescribed."
extracted_drugs = extract_drug_names(corrected_text)
print("Extracted Drugs:", extracted_drugs)





 


