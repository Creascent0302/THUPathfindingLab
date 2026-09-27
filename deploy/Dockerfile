FROM node:22-bookworm-slim AS frontend
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm
WORKDIR /app
COPY requirements.lock pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.lock
COPY pathlab/ ./pathlab/
COPY algorithms/ ./algorithms/
COPY algorithms.json ./
COPY student_template/ ./student_template/
COPY docs/student-guide.md ./docs/student-guide.md
COPY --from=frontend /ui/dist ./frontend/dist
RUN mkdir artifacts && chown 1000:1000 artifacts
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 1000:1000
CMD ["timeout", "--signal=TERM", "--kill-after=10s", "14400", "python", "-m", "uvicorn", "pathlab.api:create_app", "--factory", "--host", "127.0.0.1", "--port", "8000", "--limit-concurrency", "12", "--no-access-log"]
