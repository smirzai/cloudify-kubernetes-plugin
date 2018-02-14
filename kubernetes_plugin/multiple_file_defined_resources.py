########
# Copyright (c) 2018 GigaSpaces Technologies Ltd. All rights reserved
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

from . import (
    get_kubernetes_runtime_properties,
    get_options,
    get_resource_dict_from_file,
    resource_create,
    resource_delete,
    resource_read,
    resource_update,
    resource_verify,
    set_kubernetes_runtime_properties,
    with_kubernetes_client,
    PROPERTY_FILE
)


def prepare(**kwargs):
    resources = []

    for file_path_dict in kwargs.get(
        NODE_PROPERTY_FILES,
        ctx.node.properties.get(NODE_PROPERTY_FILES, [])
    ):
        resources.append({
            'resource_dict': get_resource_dict_from_file(
                ctx.node,
                {PROPERTY_FILE: file_path_dict['resource_path']}
            ),
            'type': get_type(ctx.node, resource_dict)
        })

    set_kubernetes_runtime_properties(ctx.instance, resources=resources)


@with_kubernetes_client
def create(client, **kwargs):
    options = get_options(ctx.node, kwargs)

    # TODO
    # for resource_data in get_kubernetes_runtime_properties(ctx.instance):
    #     resource_create(client, options, **resource_data)


@with_kubernetes_client
def verify(client, **kwargs):
    options = get_options(ctx.node, kwargs)

    # TODO
    # for resource_data in get_kubernetes_runtime_properties(ctx.instance):
    #     resource_verify(client, options, **resource_data)


@with_kubernetes_client
def update(client, **kwargs):
    options = get_options(ctx.node, kwargs)

    # TODO
    # for resource_data in get_kubernetes_runtime_properties(ctx.instance):
    #     resource_update(client, options, **resource_data)


@with_kubernetes_client
def delete(client, **kwargs):
    options = get_options(ctx.node, kwargs)

    # TODO
    # for resource_data in get_kubernetes_runtime_properties(ctx.instance):
    #     resource_delete(client, options, **resource_data)
