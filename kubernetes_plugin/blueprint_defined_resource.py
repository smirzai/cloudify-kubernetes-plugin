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
    get_resource_dict_from_blueprint,
    get_type,
    resource_create,
    resource_delete,
    resource_read,
    resource_update,
    resource_verify,
    set_kubernetes_runtime_properties,
    with_kubernetes_client
)


def prepare(**kwargs):
    resource_dict = get_resource_dict_from_blueprint(ctx.node, kwargs)
    type = get_type(ctx.node, resource_dict)

    set_kubernetes_runtime_properties(
        ctx.instance,
        resource_dict=resource_dict,
        type=type
    )


@with_kubernetes_client
def create(client, **kwargs):
    resource_create(
        client,
        get_options(ctx.node, kwargs),
        **get_kubernetes_runtime_properties(ctx.instance)
    )


@with_kubernetes_client
def verify(client, **kwargs):
    resource_verify(
        client,
        get_options(ctx.node, kwargs),
        **get_kubernetes_runtime_properties(ctx.instance)
    )


@with_kubernetes_client
def update(client, **kwargs):
    resource_update(
        client,
        get_options(ctx.node, kwargs),
        **get_kubernetes_runtime_properties(ctx.instance)
    )


@with_kubernetes_client
def delete(client, **kwargs):
    resource_delete(
        client,
        get_options(ctx.node, kwargs),
        **get_kubernetes_runtime_properties(ctx.instance)
    )
