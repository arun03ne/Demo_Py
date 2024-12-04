from flask import Flask, request, jsonify
from flask_cors import CORS  # Enable Cross-Origin Requests
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import os
import json
import base64
import requests
import logging


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file
        logging.StreamHandler()  # Log to console
    ]
)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Azure Form Recognizer credentials
endpoint = "https://oai-learning.openai.azure.com/"
key = "6pJKAl6L2Kb3QolQlDw6qooTk1uj7Pa23eu1qaCcGuNriDqDsNaGJQQJ99AKACYeBjFXJ3w3AAABACOG6jv9"



def get_item_details_from_image(file_path: str, prompt_template: str, api_base: str, deployment_name: str, api_key: str, system_prompt: str):
    """
    Analyze an image file by its path to extract item details using Azure OpenAI API.
    
    Args:
        file_path (str): The path to the image file.
        prompt_template (str): The text prompt to guide the model's analysis.
        api_base (str): Azure OpenAI API base URL.
        deployment_name (str): Azure OpenAI deployment name.
        api_key (str): API key for authentication.
        system_prompt (str): System prompt for guiding the model.

    Returns:
        dict: Parsed response containing extracted item details or an error message.
    """
    logging.info("Starting Flask app"+file_path)

    try:
        # Read the image file as a Base64 string
        with open(file_path, "rb") as file:
            image_content = base64.b64encode(file.read()).decode("utf-8")

        # Construct the API endpoint
        base_url = f"{api_base}openai/deployments/{deployment_name}"
        endpoint = f"{base_url}/chat/completions?api-version=2023-05-15"

        # Prepare the request payload
        data = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_template},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_content}"}}
                    ]
                }
            ],
            "max_tokens": 2000
        }

        # Make the HTTP POST request
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }
        response = requests.post(endpoint, headers=headers, json=data)

        if response.status_code != 200:
            # Handle non-successful responses
            return {"error": f"Error: {response.reason}"}

        # Parse the JSON response to extract the assistant's reply
        response_data = response.json()
        assistant_content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Example processing: Extract structured items if possible
        items = []
        if assistant_content:
            try:
                # Attempt to parse the assistant's content as JSON
                items = json.loads(assistant_content)
            except json.JSONDecodeError:
                items = [{"info": assistant_content}]

        return {"items": items}

    except Exception as e:
        # Handle any exceptions gracefully
        return {"error": str(e)}



@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Route to handle file uploads and return extracted item details.
    """
    logging.info("Received a request to /analyze")

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded_file = request.files["file"]

    # Save the file temporarily
    temp_file_path = os.path.join("uploads", uploaded_file.filename)
    os.makedirs("uploads", exist_ok=True)
    uploaded_file.save(temp_file_path)

    # Analyze the document
    result = get_item_details_from_image(temp_file_path,"Please extract all item details from this invoice. Create a JSON array including the items, their quantities, and the address. Additionally, include the latitude and longitude for the address.","https://oai-learning.openai.azure.com/","gpt-4o","6pJKAl6L2Kb3QolQlDw6qooTk1uj7Pa23eu1qaCcGuNriDqDsNaGJQQJ99AKACYeBjFXJ3w3AAABACOG6jv9","You are a helpful assistant for extracting invoice data.")

    # Remove the temporary file
    os.remove(temp_file_path)

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
