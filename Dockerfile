# Use Python slim image with specified version
ARG PYTHON_VERSION=3.11.4
FROM python:${PYTHON_VERSION}-slim as base

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Prevent buffering stdout and stderr for better container logging
ENV PYTHONUNBUFFERED=1

# Install libgl1-mesa-glx to resolve libGL.so.1 dependency
RUN apt-get update && \
    apt-get install -y build-essential libzbar-dev && \
    pip install zbar

# Set working directory for the application
WORKDIR /app

# Create a non-privileged user to run the application
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Install Python dependencies from requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Switch to the non-privileged user to run the application
USER appuser

# Copy the source code into the container
COPY . .

# Expose the port that the application listens on
EXPOSE 8000

# Command to run the application using Gunicorn
CMD ["gunicorn", "app:app", "--bind=0.0.0.0:8000"]
