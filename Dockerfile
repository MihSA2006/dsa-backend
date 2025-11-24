FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .



# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt gunicorn


# Copy the Django application code
COPY . .

# Expose the port the app runs on
EXPOSE 8888

# Define the command to run the application
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8888", "backend.wsgi:application"]