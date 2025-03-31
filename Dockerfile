FROM python:3.13-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECOD=1
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "./main.py"]
