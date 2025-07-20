import io
import pandas as pd
import pdfplumber
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Initialize the FastAPI application
app = FastAPI(
    title="FinSight Invoice Analyzer",
    description="An API to analyze PDF invoices and calculate spending."
)

# --- Enable CORS for all origins ---
# This is a security requirement to allow browsers from any domain
# to make requests to this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.post("/analyze", summary="Analyze a PDF invoice for 'Contraption' items")
async def analyze_invoice(file: UploadFile = File(..., description="The PDF invoice to be analyzed.")):
    """
    Accepts a PDF file, extracts the main table, filters for rows
    where the 'Item' is 'Contraption', and sums their 'Total' column.
    """
    # Check if the uploaded file is a PDF
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    try:
        # Read the uploaded file into an in-memory buffer
        pdf_bytes = await file.read()
        pdf_stream = io.BytesIO(pdf_bytes)

        # --- 1. Extract tables from the PDF using pdfplumber ---
        all_tables = []
        with pdfplumber.open(pdf_stream) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
        
        if not all_tables:
            raise HTTPException(status_code=404, detail="No tables found in the PDF.")

        # --- 2. Convert the first extracted table to a pandas DataFrame ---
        # We assume the relevant data is in the first table found.
        # The first row of the table is used as the column headers.
        df = pd.DataFrame(all_tables[0][1:], columns=all_tables[0][0])
        
        # --- 3. Clean and process the data ---
        # Ensure the required columns exist
        if 'Item' not in df.columns or 'Total' not in df.columns:
            raise HTTPException(status_code=400, detail="PDF does not contain 'Item' and/or 'Total' columns.")

        # Filter rows where the 'Item' is 'Contraption'
        contraption_df = df[df['Item'] == 'Contraption'].copy()
        
        # Clean the 'Total' column: remove '$', ',', and convert to a number
        contraption_df['Total'] = contraption_df['Total'].str.replace('$', '', regex=False)
        contraption_df['Total'] = contraption_df['Total'].str.replace(',', '', regex=False)
        contraption_df['Total'] = pd.to_numeric(contraption_df['Total'], errors='coerce')
        
        # Drop any rows where conversion to number failed
        contraption_df.dropna(subset=['Total'], inplace=True)

        # --- 4. Calculate the sum ---
        total_sum = contraption_df['Total'].sum()

        # --- 5. Return the result in the specified JSON format ---
        return JSONResponse(content={"sum": total_sum})

    except Exception as e:
        # Catch-all for any other processing errors
        raise HTTPException(status_code=500, detail=f"An error occurred during processing: {str(e)}")

@app.get("/", summary="Root endpoint for health check")
def read_root():
    return {"status": "FinSight Analyzer API is running."}

