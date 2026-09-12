FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DB_AUTO_CREATE=1
EXPOSE 5001

# --timeout 180: local LLM chat replies can legitimately take over a minute
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5001", "--timeout", "180", "app:app"]
