FROM python:3.9-slim

WORKDIR /bot

COPY bot.py requirements.txt .

RUN apt-get update && apt-get install -y libpq-dev

RUN pip install --no-cache-dir -r requirements.txt -v

CMD ["python", "bot.py"]
