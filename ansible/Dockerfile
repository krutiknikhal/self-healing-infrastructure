
FROM python:3.12-slim

WORKDIR /ansible

# Install Docker CLI without the Docker daemon
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker-cli \
    && rm -rf /var/lib/apt/lists/*

# Install Ansible Core
RUN pip install --no-cache-dir "ansible-core>=2.17,<2.20"

# Copy Ansible files
COPY inventory.ini .
COPY test.yml .
COPY recover_nginx.yml .

CMD ["ansible-playbook", "-i", "inventory.ini", "test.yml"]
