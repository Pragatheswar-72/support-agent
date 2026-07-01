# AI Customer Support Agent — container image for the Streamlit app.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

# GEMINI_API_KEY (and optionally GEMINI_API_KEYS / GROQ_API_KEY) are provided
# at runtime: docker run -e GEMINI_API_KEY=... -p 8501:8501 support-agent
CMD ["sh", "-c", "python -m src.backend.seed && streamlit run app.py --server.port=8501 --server.address=0.0.0.0"]
