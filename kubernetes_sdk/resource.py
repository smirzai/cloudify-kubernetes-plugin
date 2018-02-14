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

import inspect


class SingleOperationApiMapping(object):

    def __init__(self, api, method, payload=None):
        self.api = api
        self.method = method
        self.payload = payload


class ApiMapping(object):

    def __init__(self, create, read, update, delete):
        if isinstance(create, dict):
            create = SingleOperationApiMapping(**create)

        if isinstance(read, dict):
            read = SingleOperationApiMapping(**read)

        if isinstance(update, dict):
            update = SingleOperationApiMapping(**update)

        if isinstance(delete, dict):
            delete = SingleOperationApiMapping(**delete)

        self.create = create
        self.read = read
        self.update = update
        self.delete = delete


class Resource(object):

    MANDATORY_FIELD_NAMES = ['apiVersion', 'metadata']

    @classmethod
    def _validate_resource_dict(cls, resource_dict):
        resource_dict_keys = resource_dict.keys()

        for field_name in cls.MANDATORY_FIELD_NAMES:
            if field_name not in resource_dict_keys:
                raise RuntimeError(
                    'Invalid resource definition. "{}" field is missing'
                    .format(field_name)
                )

    def __init__(self, type, resource_dict, api_mapping=None):
        self._validate_resource_dict(resource_dict)

        if api_mapping:
            self.api_mapping = ApiMapping(**api_mapping)

        self.kind = type.split('.')[-1]  # TODO without split ?
        self.api_version = resource_dict.get('apiVersion')
        self.metadata = resource_dict.get('metadata')
        self.spec = resource_dict.get('spec', None)

    @property
    def get_api_mapping(self):
        return self.api_mapping

    # convention:
    # object_dict - dict read fro k8s API
    # return True - resource has been created correctly and is up
    # return False - resource is still in 'creating-like' state,
    #                in high level we should retry operation
    # raise RuntimeError - resource is in failed-like state
    #                    in high level we should re-raise
    #                    as NonRecoverableError
    def verify(self, object_dict):
        raise NotImplementedError(
            'Verifying status for {} resource is not supported'
            .format(self.__class__.__name__)
        )

    def add_node_label(self, label):
        raise NotImplementedError(
            'Labeling {} resource with node label is not supported'
            .format(self.__class__.__name__)
        )


class ClusterRoleBinding(Resource):

    def __init__(self, type, resource_dict, api_mapping=None):
        super(ClusterRoleBinding, self) \
            .__init__(type, resource_dict, api_mapping)

        self.role_ref = resource_dict.get('roleRef', None)
        self.subjects = resource_dict.get('subjects', None)

        self.api_mapping = ApiMapping(
            create=SingleOperationApiMapping(
                api='RbacAuthorizationV1beta1Api',
                method='create_cluster_role_binding',
                payload='V1beta1ClusterRoleBinding'
            ),
            read=SingleOperationApiMapping(
                api='RbacAuthorizationV1beta1Api',
                method='read_cluster_role_binding',
            ),
            update=SingleOperationApiMapping(
                api='RbacAuthorizationV1beta1Api',
                method='replace_cluster_role_binding',
            ),
            delete=SingleOperationApiMapping(
                api='RbacAuthorizationV1beta1Api',
                method='delete_cluster_role_binding',
                payload='V1DeleteOptions'
            )
        )


class Deployment(Resource):

    def __init__(self, type, resource_dict, api_mapping=None):
        super(Deployment, self) \
            .__init__(type, resource_dict, api_mapping)

        self.api_mapping = ApiMapping(
            create=SingleOperationApiMapping(
                api='ExtensionsV1beta1Api',
                method='create_namespaced_deployment',
                payload='AppsV1beta1Deployment'
            ),
            read=SingleOperationApiMapping(
                api='ExtensionsV1beta1Api',
                method='read_namespaced_deployment',
            ),
            update=SingleOperationApiMapping(
                api='ExtensionsV1beta1Api',
                method='replace_namespaced_deployment',
            ),
            delete=SingleOperationApiMapping(
                api='ExtensionsV1beta1Api',
                method='delete_namespaced_deployment',
                payload='V1DeleteOptions'
            )
        )

    # TODO - make it working - here only to show idea
    def add_node_label(self, label):
        self.spec.update({
            'template': {
                'spec': {'nodeSelector': label}
            }
        })

    # TODO adjust to new convention
    def verify(self, object_dict):
        conditions = object_dict['status']['conditions']

        if isinstance(conditions, list):
            for condition in conditions:
                if condition['type'] == 'Available':
                    # TODO logger ?
                    ctx.logger.debug('Deployment condition is Available')
                    return True

                elif condition['type'] == 'ReplicaFailure':
                    raise RuntimeError(
                        'Deployment condition is ReplicaFailure ,'
                        'reason:{0}, message: {1}'
                        ''.format(condition['reason'], condition['message'])
                    )

                elif condition['type'] == 'Progressing':
                    return False

        return False


class Pod(Resource):

    def __init__(self, type, resource_dict, api_mapping=None):
        super(Pod, self) \
            .__init__(type, resource_dict, api_mapping)

        self.api_mapping = ApiMapping(
            create=SingleOperationApiMapping(
                api='CoreV1Api',
                method='create_namespaced_pod',
                payload='V1Pod'
            ),
            read=SingleOperationApiMapping(
                api='CoreV1Api',
                method='read_namespaced_pod',
            ),
            update=SingleOperationApiMapping(
                api='CoreV1Api',
                method='replace_namespaced_pod'
            ),
            delete=SingleOperationApiMapping(
                api='CoreV1Api',
                method='delete_namespaced_pod',
                payload='V1DeleteOptions'
            )
        )

    # TODO adjust to new convention
    def verify(self, object_dict):
        status = object_dict['status']['phase']

        if status in ['Failed']:
            raise NonRecoverableError(
                'status {0} in phase {1}'.format(
                    status, ['Failed']))
        elif status in ['Pending', 'Unknown']:
            raise OperationRetry(
                'status {0} in phase {1}'.format(
                    status, ['Pending', 'Unknown']))
        elif status in ['Running', 'Succeeded']:
            ctx.logger.debug(
                'status {0} in phase {1}'.format(
                    status, ['Running', 'Succeeded']))


class ReplicaSet(Resource):

    def __init__(self, type, resource_dict, api_mapping=None):
        super(ReplicaSet, self) \
            .__init__(type, resource_dict, api_mapping)

        self.api_mapping = ApiMapping(
            create=SingleOperationApiMapping(
                api='ExtensionsV1beta1Api',
                method='create_namespaced_replica_set',
                payload='V1beta1ReplicaSet'
            ),
            read=SingleOperationApiMapping(
                api='ExtensionsV1beta1Api',
                method='read_namespaced_replica_set',
            ),
            update=SingleOperationApiMapping(
                api='ExtensionsV1beta1Api',
                method='replace_namespaced_replica_set'
            ),
            delete=SingleOperationApiMapping(
                api='ExtensionsV1beta1Api',
                method='delete_namespaced_replica_set',
                payload='V1DeleteOptions'
            )
        )

    # TODO adjust to new convention
    def verify(self, object_dict):
        ready_replicas = object_dict['status'].get('ready_replicas')
        replicas = object_dict['status'].get('replicas')

        if ready_replicas is None:
            raise OperationRetry(
                '{0} status not ready yet'.format(resource_kind))

        elif ready_replicas != replicas:
            raise OperationRetry(
                'Only {0} of {1} replicas are ready'.format(
                    ready_replicas, replicas))

        elif ready_replicas == replicas:
            ctx.logger.debug('All {0} replicas are ready now'.format(replicas))


class ReplicationController(Resource):

    def __init__(self, type, resource_dict, api_mapping=None):
        super(ReplicationController, self) \
            .__init__(type, resource_dict, api_mapping)

        self.api_mapping = ApiMapping(
            create=SingleOperationApiMapping(
                api='CoreV1Api',
                method='create_namespaced_replication_controller',
                payload='V1ReplicationController'
            ),
            read=SingleOperationApiMapping(
                api='CoreV1Api',
                method='read_namespaced_replication_controller',
            ),
            update=SingleOperationApiMapping(
                api='CoreV1Api',
                method='replace_namespaced_replication_controller',
            ),
            delete=SingleOperationApiMapping(
                api='CoreV1Api',
                method='delete_collection_namespaced_replication_controller',
            ),
        )

    # TODO adjust to new convention
    def verify(self, object_dict):
        ready_replicas = object_dict['status'].get('ready_replicas')
        replicas = object_dict['status'].get('replicas')

        if ready_replicas is None:
            raise OperationRetry(
                '{0} status not ready yet'.format(resource_kind))

        elif ready_replicas != replicas:
            raise OperationRetry(
                'Only {0} of {1} replicas are ready'.format(
                    ready_replicas, replicas))

        elif ready_replicas == replicas:
            ctx.logger.debug('All {0} replicas are ready now'.format(replicas))


class Service(Resource):

    def __init__(self, type, resource_dict, api_mapping=None):
        super(Service, self) \
            .__init__(type, resource_dict, api_mapping)

        self.api_mapping = ApiMapping(
            create=SingleOperationApiMapping(
                api='CoreV1Api',
                method='create_namespaced_service',
                payload='V1Service'
            ),
            read=SingleOperationApiMapping(
                api='CoreV1Api',
                method='read_namespaced_service',
            ),
            update=SingleOperationApiMapping(
                api='CoreV1Api',
                method='replace_namespaced_service'
            ),
            delete=SingleOperationApiMapping(
                api='CoreV1Api',
                method='delete_namespaced_service',
                payload='V1DeleteOptions'
            ),
        )

    # TODO adjust to new convention
    def verify(self, object_dict):
        status = object_dict.get('status')
        load_balancer = status.get('load_balancer')
        if load_balancer and load_balancer.get('ingress') is None:
            raise OperationRetry(
                'status {0} in phase {1}'.format(
                    status,
                    [{'load_balancer': {'ingress': None}}]))
        else:
            ctx.logger.debug('status {0}'.format(status))


class PersistentVolume(Resource):

    def __init__(self, type, resource_dict, api_mapping=None):
        super(PersistentVolume, self) \
            .__init__(type, resource_dict, api_mapping)

        self.api_mapping = ApiMapping(
            create=SingleOperationApiMapping(
                api='CoreV1Api',
                method='create_persistent_volume',
                payload='V1PersistentVolume'
            ),
            read=SingleOperationApiMapping(
                api='CoreV1Api',
                method='read_persistent_volume',
            ),
            update=SingleOperationApiMapping(
                api='CoreV1Api',
                method='replace_persistent_volume'
            ),
            delete=SingleOperationApiMapping(
                api='CoreV1Api',
                method='delete_persistent_volume',
                payload='V1DeleteOptions'
            ),
        )

    # TODO adjust to new convention
    def verify(self, object_dict):
        status = object_dict['status']['phase']

        if status in ['Bound', 'Available']:
            ctx.logger.debug('PersistentVolume status is {0}'.format(status))

        else:
            raise OperationRetry(
                'Unknown PersistentVolume status {0}'.format(status))


class StorageClass(Resource):

    def __init__(self, type, resource_dict, api_mapping=None):
        super(StorageClass, self) \
            .__init__(type, resource_dict, api_mapping)

        self.parameters = resource_dict.get('spec', None)
        self.provisioner = resource_dict.get('provisioner', None)

        self.api_mapping = ApiMapping(
            create=SingleOperationApiMapping(
                api='StorageV1beta1Api',
                method='create_storage_class',
                payload='V1beta1StorageClass'
            ),
            read=SingleOperationApiMapping(
                api='StorageV1beta1Api',
                method='read_storage_class',
            ),
            update=SingleOperationApiMapping(
                api='StorageV1beta1Api',
                method='replace_storage_class'
            ),
            delete=SingleOperationApiMapping(
                api='StorageV1beta1Api',
                method='delete_storage_class',
                payload='V1DeleteOptions'
            ),
        )


class ConfigMap(Resource):

    def __init__(self, type, resource_dict, api_mapping=None):
        super(ConfigMap, self) \
            .__init__(type, resource_dict, api_mapping)

        self.data = resource_dict.get('data', None)

        self.api_mapping = ApiMapping(
            create=SingleOperationApiMapping(
                api='CoreV1Api',
                method='create_namespaced_config_map',
                payload='V1ConfigMap'
            ),
            read=SingleOperationApiMapping(
                api='CoreV1Api',
                method='read_namespaced_config_map',
            ),
            update=SingleOperationApiMapping(
                api='CoreV1Api',
                method='replace_namespaced_config_map'
            ),
            delete=SingleOperationApiMapping(
                api='CoreV1Api',
                method='delete_namespaced_config_map',
                payload='V1DeleteOptions'
            ),
        )

# TODO
    #
    # elif resource_kind == 'PersistentVolumeClaim':
    #     status = object_dict['status']['phase']
    #     if status in ['Pending', 'Available', 'Bound']:
    #         ctx.logger.debug('PersistentVolumeClaim status is Bound')
    #
    #     else:
    #         raise OperationRetry(
    #             'Unknown PersistentVolume status {0}'.format(status))


def get_resource(type, resource_dict, api_mapping_dict=None, **kwargs):
    if api_mapping_dict:
        return Resource(type, resource_dict, api_mapping_dict)

    module_items = globals().copy()

    for name, item in module_items.keys():
        if name.lower() == type.lower() and inspect.isclass(v):
            return item(type, resource_dict, api_mapping)

    raise RuntimeError(
        'Cannot find proper resource class '
        '(both natively supported by plugin and custom) for given parameters:'
        '\ntype={0} \ndefinition={1} \napi_mapping={2} '
        .format(type, resource_dict, api_mapping)
    )
