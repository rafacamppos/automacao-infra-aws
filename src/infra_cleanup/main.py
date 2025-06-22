#!/usr/bin/env python3
"""Centraliza a execução dos scripts de limpeza."""
import argparse
from . import clean_all
from . import cleanup_volumes


def main():
    parser = argparse.ArgumentParser(description="Executa limpezas de infraestrutura AWS")
    parser.add_argument('--region', default=None, help='Região AWS')
    parser.add_argument('--delete', action='store_true', help='Executa deleção real (default é dry-run)')
    args = parser.parse_args()

    ca_args = []
    if args.region:
        ca_args.extend(['--region', args.region])
    if args.delete:
        ca_args.append('--delete')

    cleanup_volumes.main(ca_args)
    clean_all.main(ca_args)
    


if __name__ == '__main__':
    main()

