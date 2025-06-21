# AWS Resource Cleanup Script

This repository contains a simple Python script that lists and optionally deletes common AWS resources such as EC2 instances, S3 buckets, RDS instances and Lambda functions.

## Usage

1. Install dependencies:

```bash
pip install boto3
```

2. Edit `config.py` to set your default `REGION`, `ACCOUNT_ID` and optionally
   your AWS credentials. If credentials are left blank, the script falls back to
   the standard AWS CLI configuration or environment variables.

3. List resources in a region (defaults to the region defined in `config.py`):

```bash
python cleanup_resources.py --region us-east-1
```

4. Delete the listed resources:

```bash
python cleanup_resources.py --region us-east-1 --delete
```

> **Warning**: Deleting resources is irreversible. Ensure you really want to remove all listed resources before using the `--delete` flag.
