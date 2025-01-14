# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from __future__ import absolute_import
import boto3
import os
import logging
import platform
import pytest
import shutil
import sys
import tempfile

from sagemaker import Session
from .utils import local_mode

logger = logging.getLogger(__name__)
logging.getLogger('boto').setLevel(logging.INFO)
logging.getLogger('boto3').setLevel(logging.INFO)
logging.getLogger('botocore').setLevel(logging.INFO)
logging.getLogger('factory.py').setLevel(logging.INFO)
logging.getLogger('auth.py').setLevel(logging.INFO)
logging.getLogger('connectionpool.py').setLevel(logging.INFO)


dir_path = os.path.dirname(os.path.realpath(__file__))


def pytest_addoption(parser):
    parser.addoption('--build-image', '-D', action='store_true')
    parser.addoption('--build-base-image', '-B', action='store_true')
    parser.addoption('--aws-id')
    parser.addoption('--instance-type', default='local')
    parser.addoption('--install-container-support', '-C', action='store_true')
    parser.addoption('--docker-base-name', default='sk-learn')
    parser.addoption('--region', default='us-west-2')
    parser.addoption('--framework-version', default='1.0.2')
    parser.addoption('--py-version', choices=['2', '3'], default=str(sys.version_info.major))
    parser.addoption('--processor', choices=['cpu'], default='cpu')
    # If not specified, will default to {framework-version}-{processor}-py{py-version}
    parser.addoption('--tag', default=None)


@pytest.fixture(scope='session', name='docker_base_name')
def fixture_docker_base_name(request):
    return request.config.getoption('--docker-base-name')


@pytest.fixture(scope='session', name='region')
def fixture_region(request):
    return request.config.getoption('--region')


@pytest.fixture(scope='session', name='framework_version')
def fixture_framework_version(request):
    return request.config.getoption('--framework-version')


@pytest.fixture(scope='session', name='py_version')
def fixture_py_version(request):
    return 'py{}'.format(int(request.config.getoption('--py-version')))


@pytest.fixture(scope='session', name='processor')
def fixture_processor(request):
    return request.config.getoption('--processor')


@pytest.fixture(scope='session', name='tag')
def fixture_tag(request, framework_version, processor, py_version):
    provided_tag = request.config.getoption('--tag')
    default_tag = '{}-{}-{}'.format(framework_version, processor, py_version)
    return provided_tag if provided_tag else default_tag


@pytest.fixture(scope='session', name='docker_image')
def fixture_docker_image(docker_base_name, tag):
    return '{}:{}'.format(docker_base_name, tag)


@pytest.fixture
def opt_ml():
    tmp = tempfile.mkdtemp()
    os.mkdir(os.path.join(tmp, 'output'))

    # Docker cannot mount Mac OS /var folder properly see
    # https://forums.docker.com/t/var-folders-isnt-mounted-properly/9600
    opt_ml_dir = '/private{}'.format(tmp) if platform.system() == 'Darwin' else tmp
    yield opt_ml_dir

    shutil.rmtree(tmp, True)


@pytest.fixture(scope='session', name='install_container_support', autouse=True)
def fixture_install_container_support(request):
    install = request.config.getoption('--install-container-support')
    if install:
        local_mode.install_container_support()


@pytest.fixture(scope='session', name='build_base_image', autouse=True)
def fixture_build_base_image(request, framework_version, py_version, processor, tag, docker_base_name):
    build_base_image = request.config.getoption('--build-base-image')
    if build_base_image:
        return local_mode.build_base_image(framework_name=docker_base_name,
                                           framework_version=framework_version,
                                           py_version=py_version,
                                           base_image_tag=tag,
                                           processor=processor,
                                           cwd=os.path.join(dir_path, '..'))

    return tag


@pytest.fixture(scope='session', name='build_image', autouse=True)
def fixture_build_image(request, framework_version, py_version, processor, tag, docker_base_name):
    build_image = request.config.getoption('--build-image')
    if build_image:
        return local_mode.build_image(framework_name=docker_base_name,
                                      framework_version=framework_version,
                                      py_version=py_version,
                                      processor=processor,
                                      tag=tag,
                                      cwd=os.path.join(dir_path, '..'))

    return tag


@pytest.fixture(scope='session', name='sagemaker_session')
def fixture_sagemaker_session(region):
    return Session(boto_session=boto3.Session(region_name=region))


@pytest.fixture(name='aws_id', scope='session')
def fixture_aws_id(request):
    return request.config.getoption('--aws-id')


@pytest.fixture(name='instance_type', scope='session')
def fixture_instance_type(request):
    return request.config.getoption('--instance-type')


@pytest.fixture(name='docker_registry', scope='session')
def fixture_docker_registry(aws_id, region):
    return '{}.dkr.ecr.{}.amazonaws.com'.format(aws_id, region)


@pytest.fixture(name='ecr_image', scope='session')
def fixture_ecr_image(docker_registry, docker_base_name, tag):
    return '{}/{}:{}'.format(docker_registry, docker_base_name, tag)


@pytest.fixture(scope='session', name='dist_cpu_backend', params=['tcp', 'gloo'])
def fixture_dist_cpu_backend(request):
    return request.param
