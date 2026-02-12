from flask import Flask, request, jsonify, Response
import pdfplumber
import re
import json
import os
from io import BytesIO

app = Flask(__name__)

# ------------------------------
# Home Route
# ------------------------------
@app.route('/')
def home():
    return "Invoice Extraction Server Running Successfully!"


# ------------------------------
# Helper: Extract Text From PDF
# ------------------------------
def extract_text_from_pdf(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text


# ------------------------------
# Extract Route
# ------------------------------
@app.route('/extract', methods=['POST'])
def extract_invoice_details():

    # Case 1: multipart/form-data (Postman)
    if 'file' in request.files:
        pdf_file = request.files['file']

    # Case 2: raw binary (Power Automate HTTP action)
    elif request.data:
        pdf_file = BytesIO(request.data)

    else:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        text = extract_text_from_pdf(pdf_file)

        # --------------------------
        # Extraction Logic (Regex)
        # --------------------------

        invoice_number = re.search(r'Invoice\s*No\.?\s*[:\-]?\s*(\S+)', text)
        customer_id = re.search(r'Customer\s*(No|Number)?\.?\s*[:\-]?\s*(\S+)', text)
        invoice_period = re.search(r'(\d{2}\.\d{2}\.\d{4}\s*-\s*\d{2}\.\d{2}\.\d{4})', text)
        invoice_date = re.search(r'\d{1,2}\.\s*[A-Za-zäöüÄÖÜ]+\s*\d{4}', text)
        gross_amount = re.search(r'([\d.,]+\s*€)', text)

        response_data = {
            "invoice_number": invoice_number.group(1) if invoice_number else "Not found",
            "customer_id": customer_id.group(2) if customer_id else "Not found",
            "invoice_period": invoice_period.group(1) if invoice_period else "Not found",
            "invoice_date": invoice_date.group(0) if invoice_date else "Not found",
            "gross_amount_incl_vat": gross_amount.group(1) if gross_amount else "Not found"
        }

        return Response(
            json.dumps(response_data, ensure_ascii=False),
            content_type="application/json; charset=utf-8"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------
# Run App (Render Compatible)
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
