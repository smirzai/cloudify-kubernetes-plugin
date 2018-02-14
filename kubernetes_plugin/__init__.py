########
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import sys
import yaml

from cloudify.exceptions import (
    OperationRetry,
    RecoverableError,
    NonRecoverableError
)
from cloudify.utils import exception_to_error_cause

from kubernetes_sdk import (
    get_mapping,
    get_resource,
    CloudifyKubernetesClient,
    KubernetesApiAuthenticationVariants,
    KubernetesApiConfigurationVariants,
    KuberentesApiInitializationFailedError,
    KuberentesInvalidPayloadClassError,
    KuberentesInvalidApiClassError,
    KuberentesInvalidApiMethodError,
    KuberentesMappingNotFoundError
)


PROPERTY_AUTHENTICATION = 'authentication'
PROPERTY_CONFIGURATION = 'configuration'
RELATIONSHIP_TYPE_MANAGED_BY_MASTER = (
    'cloudify.kubernetes.relationships.managed_by_master'
)

DEFAULT_NAMESPACE = 'default'
PROPERTY_API_MAPPING = 'api_mapping'
PROPERTY_DEFINITION = 'definition'
PROPERTY_FILE = 'file'
PROPERTY_FILE_RESOURCE_PATH = 'resource_path'
PROPERTY_FILES = 'files'
PROPERTY_ID = 'id'
PROPERTY_OPTIONS = 'options'
PROPERTY_TYPE = 'type'


RUNTIME_PROPERTY_RESOURCE_DICT = 'resource_dict'
RUNTIME_PROPERTY_ID = 'id'
RUNTIME_PROPERTY_TYPE = 'type'
RUNTIME_PROPERTY_API_MAPPING_DICT = 'api_mapping_dict'
RUNTIME_PROPERTY_RESOURCES = 'resources'

RUNTIME_PROPERTIES = [
    RUNTIME_PROPERTY_RESOURCE_DICT,
    RUNTIME_PROPERTY_ID,
    RUNTIME_PROPERTY_TYPE,
    RUNTIME_PROPERTY_API_MAPPING_DICT,
    RUNTIME_PROPERTY_RESOURCES
]


# TODO
# def _get_id(resource_instance, file=None):
#     data = resource_instance.runtime_properties[
#         RUNTIME_PROPERTY_KUBERNETES
#     ]
#
#     if isinstance(data, dict) and file:
#         data = data[file]
#
#     return data['metadata']['name']
#
#


def _get_master(resource_instance):
    for relationship in resource_instance.relationships:
        if relationship.type == RELATIONSHIP_TYPE_MANAGED_BY_MASTER:
            return relationship.target


def _get_property(resource_instance, property_name):
    target = _get_master(resource_instance)
    configuration = target.node.properties.get(property_name, {})
    configuration.update(
        target.instance.runtime_properties.get(property_name, {})
    )

    return configuration


def _yaml_from_file(
        resource_path,
        target_path=None,
        template_variables=None):

    template_variables = template_variables or {}

    downloaded_file_path = \
        ctx.download_resource_and_render(
            resource_path,
            target_path,
            template_variables)

    with open(downloaded_file_path) as outfile:
        file_content = outfile.read()

    return yaml.load(file_content)


def get_options(node, kwargs):
    options = node.properties.get(PROPERTY_OPTIONS, kwargs)

    if 'namespace' not in kwargs:
        options['namespace'] = DEFAULT_NAMESPACE

    return options


def get_resource_dict_from_blueprint(node, parameters):
    resource_dict = parameters.get(
        PROPERTY_DEFINITION,
        node.properties.get(PROPERTY_DEFINITION, None)
    )

    if not resource_dict:
        raise KuberentesInvalidDefinitionError(
            'Incorrect format of resource definition'
        )

    # TODO ???
    # if 'kind' not in resource_dict:
    #     resource_dict['kind'] = node.type \
    #         if isinstance(node.type, basestring) \
    #         else ''

    return resource_dict


def get_resource_dict_from_file(node, parameters):
    file_resource = parameters.get(
        PROPERTY_FILE,
        node.properties.get(PROPERTY_FILE, None)
    )

    if not file_resource:
        raise KuberentesInvalidDefinitionError(
            'Invalid resource file definition'
        )

    return _yaml_from_file(**file_resource)


def get_type(node, resource_dict):
    return resource_dict.get('kind', node.type.split('.')[-1])


def get_kubernetes_runtime_properties(instance):
    return dict(
        (key, value)
        for key, value
        in instance.runtime_properties.iteritems()
        if key in RUNTIME_PROPERTIES
    )


def set_kubernetes_runtime_properties(instance, **kwargs):
    for key, value in kwargs.iteritems():
        if key in RUNTIME_PROPERTIES:
            instance.runtime_properties[key] = value


def delete_kubernetes_runtime_properties(instance):
    for key in RUNTIME_PROPERTIES:
        if key in instance.runtime_properties.keys():
            instance.runtime_properties.pop(key)


# TODO ??
# def resource_task(retrieve_resource_definition, retrieve_mapping):
#     def decorator(task, **kwargs):
#         def wrapper(**kwargs):
#             try:
#                 kwargs['resource_definition'] = \
#                     retrieve_resource_definition(**kwargs)
#                 kwargs['api_mapping'] = retrieve_mapping(**kwargs)
#                 task(**kwargs)
#             except (KuberentesMappingNotFoundError,
#                     KuberentesInvalidPayloadClassError,
#                     KuberentesInvalidApiClassError,
#                     KuberentesInvalidApiMethodError) as e:
#                 raise NonRecoverableError(str(e))
#             except OperationRetry as e:
#                 _, exc_value, exc_traceback = sys.exc_info()
#                 raise OperationRetry(
#                     '{0}'.format(str(e)),
#                     causes=[exception_to_error_cause(exc_value, exc_traceback)]
#                 )
#             except NonRecoverableError as e:
#                 _, exc_value, exc_traceback = sys.exc_info()
#                 raise NonRecoverableError(
#                     '{0}'.format(str(e)),
#                     causes=[exception_to_error_cause(exc_value, exc_traceback)]
#                 )
#             except Exception as e:
#                 _, exc_value, exc_traceback = sys.exc_info()
#                 raise RecoverableError(
#                     '{0}'.format(str(e)),
#                     causes=[exception_to_error_cause(exc_value, exc_traceback)]
#                 )
#         return wrapper
#     return decorator


def with_kubernetes_client(function):
    def wrapper(**kwargs):
        configuration_property = _get_property(
            ctx.instance,
            PROPERTY_CONFIGURATION
        )

        authentication_property = _get_property(
            ctx.instance,
            PROPERTY_AUTHENTICATION
        )

        try:
            kwargs['client'] = CloudifyKubernetesClient(
                ctx.logger,
                KubernetesApiConfigurationVariants(
                    ctx.logger,
                    configuration_property,
                    download_resource=ctx.download_resource
                ),
                KubernetesApiAuthenticationVariants(
                    ctx.logger,
                    authentication_property
                )
            )

            function(**kwargs)
        except KuberentesApiInitializationFailedError as e:
            _, exc_value, exc_traceback = sys.exc_info()
            raise RecoverableError(
                '{0}'.format(str(e)),
                causes=[exception_to_error_cause(exc_value, exc_traceback)]
            )

    return wrapper


# TODO
def resource_create(client, options, resource_dict, type, **kwargs):
    return JsonCleanuper(
        client.create_resource(
            get_resource(resource_dict, type, **kwargs),
            options
        )
    ).to_dict()


# TODO
def resource_read(client, options, resource_dict, type, **kwargs):

    return JsonCleanuper(
        client.read_resource(
            get_resource(resource_dict, type, **kwargs),
            options
        )
    ).to_dict()


# TODO
def resource_update(client, options, resource_dict, type, **kwargs):

    return JsonCleanuper(
        client.update_resource(
            get_resource(resource_dict, type, **kwargs),
            options
        )
    ).to_dict()


# TODO
def resource_verify(client, options, resource_dict, type, **kwargs):
    pass


'''The required fields for all kubernetes resources are
- name
- namespace
- body

But the ``ReplicationController`` resource have only one required arg
which is namespace

Moreover all resources have also payload with type ``V1DeleteOptions``
except ``ReplicationController`` that does not have one

The resource is not a type of ``ReplicationController`` then we must
pass all the required fields'''


# TODO
def resource_delete(client, options, id, type, **kwargs):
    return JsonCleanuper(
        client.delete_resource(
            get_resource(resource_dict, type, **kwargs),
            options
        )
    ).to_dict()


class JsonCleanuper(object):
    def __init__(self, ob):
        resource = ob.to_dict()

        if isinstance(resource, list):
            self._cleanuped_list(resource)
        elif isinstance(resource, dict):
            self._cleanuped_dict(resource)

        self.value = resource

    def _cleanuped_list(self, resource):
        for k, v in enumerate(resource):
            if not v:
                continue
            if isinstance(v, list):
                self._cleanuped_list(v)
            elif isinstance(v, dict):
                self._cleanuped_dict(v)
            elif (not isinstance(v, int) and  # integer and bool
                  not isinstance(v, str) and
                  not isinstance(v, unicode)):
                resource[k] = str(v)

    def _cleanuped_dict(self, resource):
        for k in resource:
            if not resource[k]:
                continue
            if isinstance(resource[k], list):
                self._cleanuped_list(resource[k])
            elif isinstance(resource[k], dict):
                self._cleanuped_dict(resource[k])
            elif (not isinstance(resource[k], int) and  # integer and bool
                  not isinstance(resource[k], str) and
                  not isinstance(resource[k], unicode)):
                resource[k] = str(resource[k])

    def to_dict(self):
        return self.value
