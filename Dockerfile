FROM python:3.13-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECOD=1
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN mkdir /app/reports
RUN pip install -r requirements.txt
COPY . .
RUN chown -R 2001:2001 /app
USER 2001:2001
CMD ["python", "./main.py"]
