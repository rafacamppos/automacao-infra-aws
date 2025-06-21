import boto3
import argparse
from typing import List

import config


def get_session(region: str) -> boto3.Session:
    """Create a boto3 session using config credentials if provided."""
    if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
        return boto3.Session(
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            aws_session_token=config.AWS_SESSION_TOKEN or None,
            region_name=region,
        )
    return boto3.Session(region_name=region)


def list_ec2_instances(region: str) -> List[str]:
    session = get_session(region)
    ec2 = session.client('ec2')
    instances = ec2.describe_instances()
    ids = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            ids.append(instance['InstanceId'])
    return ids


def terminate_ec2_instances(region: str, instance_ids: List[str]):
    if not instance_ids:
        return
    session = get_session(region)
    ec2 = session.client('ec2')
    ec2.terminate_instances(InstanceIds=instance_ids)


def list_s3_buckets(region: str) -> List[str]:
    session = get_session(region)
    s3 = session.client('s3')
    response = s3.list_buckets()
    return [bucket['Name'] for bucket in response.get('Buckets', [])]


def delete_s3_bucket(region: str, name: str):
    session = get_session(region)
    s3 = session.resource('s3')
    bucket = s3.Bucket(name)
    # Delete all objects
    bucket.objects.all().delete()
    bucket.delete()


def list_rds_instances(region: str) -> List[str]:
    session = get_session(region)
    rds = session.client('rds')
    response = rds.describe_db_instances()
    return [db['DBInstanceIdentifier'] for db in response.get('DBInstances', [])]


def delete_rds_instance(region: str, instance_id: str):
    session = get_session(region)
    rds = session.client('rds')
    rds.delete_db_instance(DBInstanceIdentifier=instance_id, SkipFinalSnapshot=True)


def list_lambda_functions(region: str) -> List[str]:
    session = get_session(region)
    lam = session.client('lambda')
    funcs = lam.list_functions()
    return [fn['FunctionName'] for fn in funcs.get('Functions', [])]


def delete_lambda_function(region: str, name: str):
    session = get_session(region)
    lam = session.client('lambda')
    lam.delete_function(FunctionName=name)


SERVICES = ['ec2', 's3', 'rds', 'lambda']


def main():
    parser = argparse.ArgumentParser(description="List or delete AWS resources")
    parser.add_argument('--region', default=config.REGION, help='AWS region')
    parser.add_argument('--delete', action='store_true', help='Delete resources')
    args = parser.parse_args()

    region = args.region

    if 'ec2' in SERVICES:
        instances = list_ec2_instances(region)
        print(f"EC2 instances: {instances}")
        if args.delete and instances:
            terminate_ec2_instances(region, instances)
            print("Terminated EC2 instances")

    if 's3' in SERVICES:
        buckets = list_s3_buckets(region)
        print(f"S3 buckets: {buckets}")
        if args.delete:
            for b in buckets:
                delete_s3_bucket(region, b)
                print(f"Deleted bucket {b}")

    if 'rds' in SERVICES:
        dbs = list_rds_instances(region)
        print(f"RDS instances: {dbs}")
        if args.delete:
            for db in dbs:
                delete_rds_instance(region, db)
                print(f"Deleted RDS instance {db}")

    if 'lambda' in SERVICES:
        functions = list_lambda_functions(region)
        print(f"Lambda functions: {functions}")
        if args.delete:
            for fn in functions:
                delete_lambda_function(region, fn)
                print(f"Deleted Lambda function {fn}")


if __name__ == '__main__':
    main()
