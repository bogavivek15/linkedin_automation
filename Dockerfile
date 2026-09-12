FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if required by any python packages (e.g. for PyMuPDF or others)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Expose port 7860 for Hugging Face Spaces
EXPOSE 7860

# Run the FastAPI server on port 7860
CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "7860"]
