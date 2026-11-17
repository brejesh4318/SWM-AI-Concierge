FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUTF8=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

RUN useradd --create-home appuser
USER appuser

CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}



