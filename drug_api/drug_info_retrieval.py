from flask import Flask, request, jsonify
from flask_cors import CORS  # Import Flask-CORS
import pandas as pd
import openai
from config import OPENAI_API_KEY
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
CORS(app)  # Enable CORS for the entire app

# Define the path to the CSV files
df_path = os.path.join(current_dir,'drugbank_clean.csv')
df_prepared_path = os.path.join(current_dir,'drug_information.csv')

# Use the imported API key
openai.api_key = OPENAI_API_KEY

def get_drug_info(drug_name):
    try:
        # Load DataFrames
        df_prepared = pd.read_csv(df_prepared_path, index_col="name")
        df = pd.read_csv(df_path, low_memory=False)  # Suppress DtypeWarning
        drug_name_lower = drug_name.lower()

        # Check if the drug exists in the database
        try:
            drug_info = df_prepared.loc[df_prepared.index.str.lower() == drug_name_lower].iloc[0]
        except IndexError:
            print(f"Drug '{drug_name}' not found in the database.")
            return None

        # Process drug interactions
        if isinstance(drug_info['drug-interactions'], str):
            interactions = drug_info['drug-interactions'].split()
            mapped_interactions = []
            for interaction_id in interactions:
                try:
                    drug_name_for_id = df[df['drugbank-id'].str.lower() == interaction_id.lower()]['name'].iloc[0]
                    mapped_interactions.append(drug_name_for_id)
                except IndexError:
                    pass
            drug_info['drug-interactions'] = ', '.join(mapped_interactions)

        # Extract drug information
        drug_information = drug_info['description']
        indication = drug_info['indication']
        side_effects = drug_info['toxicity']
        interaction = f"Food Interactions: {drug_info['food-interactions']}\nDrug Interactions: {drug_info['drug-interactions']}"

        return drug_information, indication, side_effects, interaction

    except (KeyError, IndexError) as e:
        print(f"Error processing drug information: {e}")
        return None

def get_medicine_price(medicine_name):
    try:
        response = openai.ChatCompletion.create(  # Correct new API call
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant that provides estimated medicine prices in the Philippines."},
                {"role": "user", "content": f"What is the estimated price of {medicine_name} in Mercury Drug, Southstar Drug, and Watsons in the Philippines?"}
            ]
        )

        return response['choices'][0]['message']['content']  # Updated response parsing

    except openai.error.OpenAIError as e:  # Updated error handling
        return f"Error: {str(e)}"

def get_dosage_guidelines(medicine_name, raw_text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a medical assistant that restructures unstructured dosage guidelines into a structured format based on raw text and medicine names."},
                {"role": "user", "content": f"Restructure the following unstructured dosage guideline for the medicine '{medicine_name}' into the format below:\n\nUse for: [Condition/Body part]\n\nSig (Directions): [Dosage instructions]\n\nRaw text:\n{raw_text}"}
            ]
        )

        return response['choices'][0]['message']['content']  # Extract the response content

    except openai.error.OpenAIError as e:
        return f"Error: {str(e)}"


@app.route('/get-drug-info', methods=['POST'])
def get_drug_info_endpoint():
    data = request.get_json()
    drug_name = data.get('drug_name',[])
    result = get_drug_info(drug_name)
    
    if result:
        drug_information, indication, side_effects, interaction = result
        price = get_medicine_price(drug_name)
        dosage = get_dosage_guidelines(drug_name, data.get('raw_text', ''))
        return jsonify({
            "drug_information": drug_information,
            "indication": indication,
            "dosage":dosage,
            "side_effects": side_effects,
            "interaction": interaction,
            "price": price
        })
    else:
        return jsonify({"error": f"Drug '{drug_name}' not found in the database."}), 404

@app.route('/process-raw-text', methods=['POST'])
def process_raw_text():
    try:
        data = request.get_json()
        raw_text = data.get('raw_text', '')

        if not raw_text:
            return jsonify({"success": False, "error": "No raw text provided"}), 400

        # Process the raw text (e.g., extract drug information)
        print(f"Received raw text: {raw_text}")
        # Add your drug information retrieval logic here

        # Example response
        return jsonify({"success": True, "message": "Raw text processed successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



if __name__ == "__main__":
    app.run(debug=True, port=5000)
