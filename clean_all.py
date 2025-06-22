#!/usr/bin/env python3
import argparse
import boto3
import json
import sys
from botocore.exceptions import NoCredentialsError, ClientError

# Caminhos dos arquivos de configuração
CREDENTIALS_PATH = 'config/credentials.json'
CONFIG_PATH = 'config/cleanup_config.json'
dry_run = False


def load_credentials(path):
    """
    Carrega Access Key e Secret Access Key de um arquivo JSON.
    """
    try:
        with open(path, 'r') as f:
            creds = json.load(f)
        return creds.get('aws_access_key_id'), creds.get('aws_secret_access_key')
    except FileNotFoundError:
        print(f"❌ Arquivo de credenciais nao encontrado: {path}", file=sys.stderr)
        sys.exit(1)


def load_config(path):
    with open(path, 'r') as f:
        return json.load(f)


def create_session(region, access_key, secret_key):
    """
    Cria boto3.Session usando credenciais carregadas.
    """
    return boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )


def list_all_resources(session):
    client = session.client('resourcegroupstaggingapi')
    paginator = client.get_paginator('get_resources')
    all_resources = []

    for page in paginator.paginate(ResourcesPerPage=100):
        all_resources.extend(page['ResourceTagMappingList'])

    return [r['ResourceARN'] for r in all_resources]


def cleanup_vpc(session, vpc_id):
    ec2_res = session.resource('ec2')
    ec2_client = session.client('ec2')
    # Disassociate and release Elastic IPs
    for addr in ec2_client.describe_addresses(Filters=[{'Name':'domain','Values':['vpc']}])['Addresses']:
        if addr.get('AssociationId'):
            print(f"Disassociating EIP {addr['AllocationId']} from {addr['AssociationId']}")
            try:
                ec2_client.disassociate_address(AssociationId=addr['AssociationId'])
                ec2_client.release_address(AllocationId=addr['AllocationId'])
            except ClientError as e:
                print(f"  ⚠️ Erro ao liberar EIP: {e}")
    # Cleanup NAT Gateways
    for nat in ec2_client.describe_nat_gateways(Filters=[{'Name':'vpc-id','Values':[vpc_id]}])['NatGateways']:
        print(f"Deleting NAT Gateway {nat['NatGatewayId']}")
        try:
            ec2_client.delete_nat_gateway(NatGatewayId=nat['NatGatewayId'])
        except ClientError as e:
            print(f"  ⚠️ Erro ao deletar NAT Gateway: {e}")
    # Detach and delete Internet Gateways
    for igw in ec2_res.internet_gateways.filter(Filters=[{'Name':'attachment.vpc-id','Values':[vpc_id]}]):
        try:
            print(f"Detaching IGW {igw.id}")
            igw.detach_from_vpc(VpcId=vpc_id)
            igw.delete()
        except ClientError as e:
            print(f"  ⚠️ Erro ao detachar/deletar IGW: {e}")
    # Delete subnets
    for subnet in ec2_res.subnets.filter(Filters=[{'Name':'vpc-id','Values':[vpc_id]}]):
        print(f"Deleting subnet {subnet.id}")
        subnet.delete()
    # Delete route table associations and tables
    for rt in ec2_client.describe_route_tables(Filters=[{'Name':'vpc-id','Values':[vpc_id]}])['RouteTables']:
        for assoc in rt.get('Associations', []):
            if not assoc.get('Main'):
                print(f"Disassociating route table {assoc['RouteTableAssociationId']}")
                ec2_client.disassociate_route_table(AssociationId=assoc['RouteTableAssociationId'])
        # delete custom route tables
        if not any(assoc.get('Main') for assoc in rt.get('Associations', [])):
            print(f"Deleting route table {rt['RouteTableId']}")
            ec2_client.delete_route_table(RouteTableId=rt['RouteTableId'])
    # Delete security groups (skip default)
    for sg in ec2_res.security_groups.filter(Filters=[{'Name':'vpc-id','Values':[vpc_id]}]):
        if sg.group_name != 'default':
            print(f"Deleting security group {sg.id}")
            sg.delete()
    # Finalmente delete a VPC
    print(f"Deleting VPC {vpc_id}")
    ec2_client.delete_vpc(VpcId=vpc_id)

def delete_arn(arn: str, session, dry_run: bool):
    svc = arn.split(':')[2]
    rid = arn.split('/')[-1]
    action = 'DRY-RUN excluir' if dry_run else 'Excluindo'
    resource = arn.split(':', 5)[5]
    rtype, rid = resource.split('/', 1)
    print(f"{action} → {svc}: {arn}")

    if dry_run == False:
        return

    try:
        # Cliente genérico para serviços suportados
        if svc == 'ec2':
            if rtype == 'instance':
                session.resource('ec2').Instance(rid).terminate()
            elif rtype == 'vpc':
                cleanup_vpc(session, rid)
            else:
                print(f"  ⚠️ Tipo EC2 não suportado para deleção automática: {rtype}")
        elif svc == 's3':
            # Extrai o nome do bucket do ARN
            bucket_name = arn.split(":::")[-1]
            bucket = session.resource('s3').Bucket(bucket_name)
            for obj in bucket.objects.all():
                obj.delete()
            bucket.delete()
        elif svc == 'lambda':
            session.client('lambda').delete_function(FunctionName=rid)
        elif svc == 'rds':
            session.client('rds').delete_db_instance(
                DBInstanceIdentifier=rid, SkipFinalSnapshot=True
            )
        elif svc == 'dynamodb':
            session.client('dynamodb').delete_table(TableName=rid)
        elif svc == 'eks':
            session.client('eks').delete_cluster(name=rid)
        elif svc == 'sqs':
            account = session.client('sts').get_caller_identity()['Account']
            url = f"https://sqs.{session.region_name}.amazonaws.com/{account}/{rid}"
            session.client('sqs').delete_queue(QueueUrl=url)
        elif svc == 'logs':
            session.client('logs').delete_log_group(logGroupName=rid)
        elif svc == 'sns':
            session.client('sns').delete_topic(TopicArn=arn)
        else:
            print(f"  ⚠️ Serviço não suportado: {svc}")
    except Exception as e:
        print(f"  ❌ Erro ao deletar {arn}: {e}")


def main():
    parser = argparse.ArgumentParser(description='Cleanup AWS: delete ALL resources via ResourceGroupsTaggingAPI')
    parser.add_argument('--region', default=None, help='Região AWS')
    parser.add_argument('--delete', action='store_true', help='Executa deleção real (default é dry-run)')
    args = parser.parse_args()

    # Carrega credenciais
    access_key, secret_key = load_credentials(CREDENTIALS_PATH)

    # Carrega config (região)
    cfg = load_config(CONFIG_PATH)
    region = args.region or cfg.get('region')

    # Cria sessão boto3
    try:
        session = create_session(region, access_key, secret_key)
    except NoCredentialsError:
        print('❌ Credenciais inválidas.', file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Listando todos os recursos em {region} (modo dry-run: {not args.delete})")
    arns = list_all_resources(session)

    if not arns:
        print("✅ Nenhum recurso retornado pela API de tagging.")
        return

    for arn in arns:
        delete_arn(arn, session, dry_run=not args.delete)

    print("✅ Processo concluído.")

if __name__ == '__main__':
    main()