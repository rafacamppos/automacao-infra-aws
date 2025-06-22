import sys
import types
import builtins
import importlib
import os
from types import SimpleNamespace

# Create dummy boto3 and botocore modules so scripts can be imported without the
# real dependencies
boto3 = types.ModuleType('boto3')
class DummySession:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
    def client(self, name):
        return self._client
boto3.Session = DummySession
sys.modules['boto3'] = boto3

botocore = types.ModuleType('botocore')
exceptions = types.ModuleType('botocore.exceptions')
class NoCredentialsError(Exception):
    pass
class ClientError(Exception):
    pass
exceptions.NoCredentialsError = NoCredentialsError
exceptions.ClientError = ClientError
botocore.exceptions = exceptions
sys.modules['botocore'] = botocore
sys.modules['botocore.exceptions'] = exceptions

import clean_all
import cleanup_volumes


def test_load_credentials(tmp_path):
    creds_file = tmp_path / 'creds.json'
    creds_file.write_text('{"aws_access_key_id": "AK", "aws_secret_access_key": "SK"}')
    ak, sk = clean_all.load_credentials(str(creds_file))
    assert ak == 'AK'
    assert sk == 'SK'


def test_create_session():
    called = {}
    class MySession(DummySession):
        def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, region_name=None):
            called['args'] = (aws_access_key_id, aws_secret_access_key, region_name)
    boto3.Session = MySession
    session = clean_all.create_session('sa-east-1', 'AK', 'SK')
    assert called['args'] == ('AK', 'SK', 'sa-east-1')
    assert isinstance(session, MySession)


def test_delete_available_volumes():
    deleted = []
    class DummyEC2:
        def describe_volumes(self, Filters=None):
            return {'Volumes': [{'VolumeId': 'v1'}, {'VolumeId': 'v2'}]}
        def delete_volume(self, VolumeId=None):
            deleted.append(VolumeId)
    class MySession(DummySession):
        def client(self, name):
            assert name == 'ec2'
            return DummyEC2()
    session = MySession()
    cleanup_volumes.delete_available_volumes(session, 'sa-east-1')
    assert deleted == ['v1', 'v2']


def test_delete_arn_instance_already_terminated(capsys):
    class DummyInstance:
        def __init__(self):
            self.state = {'Name': 'terminated'}
            self.terminated_called = False
        def terminate(self):
            self.terminated_called = True

    dummy_instance = DummyInstance()

    class DummyResource:
        def Instance(self, instance_id):
            return dummy_instance

    class MySession(DummySession):
        def resource(self, name):
            assert name == 'ec2'
            return DummyResource()

    session = MySession()
    clean_all.delete_arn('arn:aws:ec2:sa-east-1:123456789012:instance/i-123', session, dry_run=True)
    captured = capsys.readouterr().out
    assert dummy_instance.terminated_called is False
    assert 'já está encerrada' in captured
