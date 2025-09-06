# Använd en officiell Python-bild som bas
FROM python:3.9-slim

# Miljövariabler för att minska Python-cache och se loggar direkt
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Sätt arbetsmappen i containern
WORKDIR /app

# Kopiera in filen requirements.txt först och installera beroenden
# (bättre cache-hantering när du bygger om)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiera in resten av appens filer
COPY . .

# Kör botten när containern startar
CMD ["python", "slack.py"]

