FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .



# Install dependencies
RUN pip install -r requirements.txt


# Copy the Django application code
COPY . .

# Expose the port the app runs on
EXPOSE 8888

# Define the command to run the application
COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8888", "backend.wsgi:application"]