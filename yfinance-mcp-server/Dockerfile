# --- Builder Stage ---
FROM tei1988/poetry:2.1.2-alpine AS builder

# Set environment variables
# Poetry specific environment variables are likely set in the base image,
# but we define them here for clarity and potential overrides.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.1.2 \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true

# Install system dependencies required for building project dependencies (wheels) on Alpine
# build-base includes gcc, make, etc.
# libffi-dev is often needed for packages using CFFI
# curl is removed as Poetry is pre-installed
RUN apk add --no-cache build-base python3-dev libffi-dev

# Set the working directory
WORKDIR /app

# Copy dependency definition files
COPY pyproject.toml poetry.lock* ./

# Install dependencies using Poetry (only main group)
# This will create a .venv directory inside /app
RUN poetry install --no-root --only main

# --- Final Stage ---
FROM python:3.12-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Install only necessary runtime system dependencies (if any)
# For yfinance/pandas on Alpine, sometimes specific libraries might be needed at runtime.
# Start with none and add if runtime errors occur.
# RUN apk add --no-cache ...

# Set the working directory
WORKDIR /app

# Copy the virtual environment with dependencies from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy the application code
COPY src/ ./src/

# Make sure the script is executable (though python command doesn't strictly need it)
RUN chmod +x src/main.py

# Command to run the application using python from the venv (implicitly via PATH)
CMD ["python", "src/main.py"]
