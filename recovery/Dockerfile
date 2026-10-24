
# Reuse our existing Ansible image
FROM self-healing-ansible:test

# Install Flask for the recovery API
COPY requirements.txt /tmp/recovery-requirements.txt

RUN pip install --no-cache-dir -r /tmp/recovery-requirements.txt

# Copy the recovery service application
COPY app.py /recovery/app.py

# Document the internal API port
EXPOSE 5001

# Start the recovery service
CMD ["python", "/recovery/app.py"]
