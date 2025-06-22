#!/usr/bin/env python3
import json
import sys
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

# Caminho do arquivo de credenciais
CREDENTIALS_PATH = 'config/credentials.json'

def load_credentials(path):
    try:
        with open(path, 'r') as f:
            creds = json.load(f)
        return creds['aws_access_key_id'], creds['aws_secret_access_key']
    except FileNotFoundError:
        print(f"❌ Arquivo de credenciais não encontrado: {path}", file=sys.stderr)
        sys.exit(1)
    except KeyError:
        print(f"❌ Formato inválido em {path}. Deve conter aws_access_key_id e aws_secret_access_key.", file=sys.stderr)
        sys.exit(1)

def create_session(region, access_key, secret_key):
    try:
        return boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
    except NoCredentialsError:
        print("❌ Credenciais inválidas.", file=sys.stderr)
        sys.exit(1)

def delete_available_volumes(session, region, dry_run=False):
    ec2 = session.client('ec2')
    try:
        volumes = ec2.describe_volumes(
            Filters=[{'Name': 'status', 'Values': ['available']}]
        )['Volumes']
    except ClientError as e:
        print(f"❌ Erro ao listar volumes: {e}", file=sys.stderr)
        return

    if not volumes:
        print("✅ Não há volumes disponíveis para deletar.")
        return

    for v in volumes:
        vid = v['VolumeId']
        action = "DRY-RUN deleting" if dry_run else "Deleting"
        print(f"{action} volume {vid}")
        #if not dry_run:
        try:
            ec2.delete_volume(VolumeId=vid)
        except ClientError as e:
            print(f"  ❌ Erro ao deletar volume {vid}: {e}")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Limpa volumes EBS disponíveis na AWS")
    parser.add_argument('--region', default='sa-east-1', help='Região AWS (default: sa-east-1)')
    parser.add_argument('--delete', action='store_true', help='Executa deleção real (default é dry-run)')
    args = parser.parse_args()

    # Carrega credenciais e cria sessão
    ak, sk = load_credentials(CREDENTIALS_PATH)
    session = create_session(args.region, ak, sk)

    # Executa limpeza
    delete_available_volumes(session, args.region, dry_run=not args.delete)