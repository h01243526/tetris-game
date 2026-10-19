FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/

WORKDIR /app/backend

# HF Spaces Docker 默认通过 7860 端口对外暴露
ENV PORT=7860
ENV HOST=0.0.0.0

EXPOSE 7860

CMD ["gunicorn", "wsgi:application", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "4", "--timeout", "60", "--preload"]
