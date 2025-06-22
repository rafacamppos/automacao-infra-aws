# AWS Resource Cleanup Script

This repository contains a simple Python script that lists and optionally deletes common AWS resources such as EC2 instances, S3 buckets, RDS instances and Lambda functions.

## Usage

1. Install dependencies:

```bash
pip install boto3
```

2. Edit `infra_cleanup/config.py` to set your default `REGION`, `ACCOUNT_ID` and optionally
   your AWS credentials. If credentials are left blank, the script falls back to
   the standard AWS CLI configuration or environment variables.

3. List resources in a region (defaults to the region defined in `config.py`):

```bash
python -m infra_cleanup.cleanup_resources --region us-east-1
```

4. Delete the listed resources:

```bash
python -m infra_cleanup.cleanup_resources --region us-east-1 --delete
```

> **Warning**: Deleting resources is irreversible. Ensure you really want to remove all listed resources before using the `--delete` flag.

## Docker

A Docker image is built and published automatically to Docker Hub from the `main` branch. You can run the cleanup scripts using:

```bash
docker run --rm -v $(pwd)/config:/app/config DOCKERHUB_USERNAME/automacao-infra-aws:latest
```

Replace `DOCKERHUB_USERNAME` with the Docker Hub user configured in the workflow secrets.
