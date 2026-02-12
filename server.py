from flask import Flask, request, Response
import pdfplumber
import re
import json
import os

app = Flask(__name__)

# ---------------------------------------------------
# Home Route
# ---------------------------------------------------
@app.route('/')
def home():
    return "Invoice Extraction Server Running Successfully!"


# ---------------------------------------------------
# Extract Text From PDF
# ---------------------------------------------------
def extract_text_from_pdf(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


# ---------------------------------------------------
# Main Extraction Route
# ---------------------------------------------------
@app.route('/extract', methods=['POST'])
def extract_invoice_details():

    if 'file' not in request.files:
        return Response(
            json.dumps({"error": "No file uploaded"}, ensure_ascii=False),
            content_type="application/json; charset=utf-8"
        ), 400

    pdf_file = request.files['file']

    try:
        text = extract_text_from_pdf(pdf_file)

        # ---------------------------------------------------
        # Extract Table Row:
        # 123100401 12345 01.02.2024 - 29.02.2024 1. März 2024
        # ---------------------------------------------------
        table_match = re.search(
            r"(\d{9})\s+(\d+)\s+(\d{2}\.\d{2}\.\d{4}\s*-\s*\d{2}\.\d{2}\.\d{4})\s+([0-9.\sA-Za-zäöüÄÖÜß]+2024)",
            text
        )

        invoice_number = table_match.group(1) if table_match else "Not found"
        customer_id = table_match.group(2) if table_match else "Not found"
        invoice_period = table_match.group(3) if table_match else "Not found"
        invoice_date = table_match.group(4).strip() if table_match else "Not found"

        # ---------------------------------------------------
        # Extract Gross Amount incl. VAT
        # ---------------------------------------------------
        gross_match = re.search(
            r"Gross Amount incl\. VAT\s+([\d,]+\s?€)",
            text
        )

        gross_amount = gross_match.group(1) if gross_match else "Not found"

        response_data = {
            "invoice_number": invoice_number,
            "customer_id": customer_id,
            "invoice_period": invoice_period,
            "invoice_date": invoice_date,
            "gross_amount_incl_vat": gross_amount
        }

        # ---------------------------------------------------
        # Optional Dynamic Fields (from Copilot)
        # ---------------------------------------------------
        extra_fields = request.form.get("extra_fields")

        if extra_fields:
            field_list = [field.strip() for field in extra_fields.split(",")]

            for field in field_list:
                pattern = rf"{field}\s+([\d,\.]+\s?€?)"
                match = re.search(pattern, text, re.IGNORECASE)

                if match:
                    response_data[field] = match.group(1)
                else:
                    response_data[field] = "Not found"

        # ---------------------------------------------------
        # Return JSON without Unicode escaping
        # ---------------------------------------------------
        return Response(
            json.dumps(response_data, ensure_ascii=False),
            content_type="application/json; charset=utf-8"
        )

    except Exception as e:
        return Response(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            content_type="application/json; charset=utf-8"
        ), 500


# ---------------------------------------------------
# Run Server
# ---------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

