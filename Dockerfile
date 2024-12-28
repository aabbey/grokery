# Use the official Python 3.13 slim image as the base image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
ENV PORT=8000
ENV DJANGO_SETTINGS_MODULE=groc.settings

# Set the working directory
WORKDIR /app

# Install system dependencies and Poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && poetry config virtualenvs.create false \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

# Copy just the dependency files first
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Copy the rest of the application code
COPY . .

# Install the project itself
RUN poetry install --no-interaction --no-ansi

# Collect static files
RUN poetry run python manage.py collectstatic --noinput

# Expose the port the app runs on
EXPOSE $PORT

# Create a script to run migrations and start the server
RUN echo '#!/bin/sh\n\
poetry run python manage.py migrate --noinput\n\
poetry run uvicorn groc.asgi:application --host 0.0.0.0 --port $PORT --workers 4' > /app/start.sh \
    && chmod +x /app/start.sh

# Run the start script
CMD ["/app/start.sh"]
