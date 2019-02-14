# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import re
import os
from enum import Enum

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse  # pylint: disable=import-error

from knack.util import CLIError

from msrestazure.tools import is_valid_resource_id, resource_id
from azure.cli.core.commands.client_factory import get_subscription_id


class SourceType(Enum):
    PLATFORM_IMAGE = "platform"
    ISO_URI = "iso"

from knack.log import get_logger
logger = get_logger(__name__)

def _parse_script(script_str):
    script = {"script": script_str}
    if urlparse(script_str).scheme and "://" in script_str:
        logger.info("{} appears to be a url.".format(script_str))
        script["is_url"] = True
    else:
        logger.info("{} does not look like a url. Assuming it is a file.".format(script_str))
        script["is_url"] = False
        if not os.path.isfile(script_str):
            raise CLIError("Script file {} does not exist.".format(script_str))
    return script


def _parse_managed_image_destination(cmd, rg, destination):

    if any([not destination, "=" not in destination]):
        raise CLIError("Invalid Format: the given image destination {} must be a string that contains the '=' delimiter.".format(destination))

    id, location = destination.rsplit(sep="=", maxsplit=1)
    if not id or not location:
        raise CLIError("Invalid Format: destination {} should have format 'destination=location'.".format(destination))

    if not is_valid_resource_id(id):
        id = resource_id(
            subscription=get_subscription_id(cmd.cli_ctx),
            resource_group=rg,
            namespace='Microsoft.Compute', type='images',
            name=id
        )

    return id, location


def _parse_shared_image_destination(cmd, rg, destination):

    if any([not destination, "=" not in destination]):
        raise CLIError("Invalid Format: the given image destination {} must be a string that contains the '=' delimiter.".format(destination))

    id, location = destination.rsplit(sep="=", maxsplit=1)

    if not id or not location:
        raise CLIError("Invalid Format: destination {} should have format 'destination=location'.".format(destination))

    if not is_valid_resource_id(id):
        if "=" not in id:
            raise CLIError("Invalid Format: {} must have a shared image gallery name and definition. They must be delimited by a '='.".format(id))

        sig_name, sig_def = destination.rsplit(sep="=", maxsplit=1)

        id = resource_id(
            subscription=get_subscription_id(cmd.cli_ctx), resource_group=rg,
            namespace='Microsoft.Compute',
            type='galleries', name=sig_name,
            child_type_1='images', child_name_1=sig_def
        )

    return (id, destination.split(","))

# STILL NEED TO VALIDATE THAT EACH LOCATION IS IN THE SUBSCRIPTION....

def validate_image_template_create(cmd, namespace):
    source = None
    scripts = []

    # Validate and parse scripts
    for ns_script in namespace.scripts:
        scripts.append(_parse_script(ns_script))


    # Validate and parse destination and locations

    # Validate and parse source image
    # 1 - check if source is a URN. A urn e.g "Canonical:UbuntuServer:18.04-LTS:latest"
    urn_match = re.match('([^:]*):([^:]*):([^:]*):([^:]*)', namespace.source)
    if urn_match: # if platform image urn
        source = {
            'os_publisher': urn_match.group(1),
            'os_offer': urn_match.group(2),
            'os_sku': urn_match.group(3),
            'os_version': urn_match.group(4),
            'type': SourceType.PLATFORM_IMAGE
        }

    # 2 - check if source is a Redhat iso uri. If so a checksum must be provided.
    elif urlparse(namespace.source).scheme and "://" in namespace.source and ".iso" in namespace.source.lower():
        if not namespace.checksum:
            raise CLIError("Must provide a checksum for source uri.", )
        source = {
            'uri': namespace.source,
            'check_sum': namespace.checksum,
            'type': SourceType.ISO_URI
        }
    # 3 - check if source is a urn alias from the vmImageAliasDoc endpoint. See "az cloud show"
    else:
        from azure.cli.command_modules.vm._actions import load_images_from_aliases_doc
        images = load_images_from_aliases_doc(cmd.cli_ctx)
        matched = next((x for x in images if x['urnAlias'].lower() == namespace.source.lower()), None)
        if matched:
            source = {
                'os_publisher': matched['publisher'],
                'os_offer': matched['offer'],
                'os_sku': matched['sku'],
                'os_version': matched['version'],
                'type': SourceType.PLATFORM_IMAGE
            }

    if not source:
        err = 'Invalid image "{}". Use a valid image URN, ISO URI, or pick a platform image alias from {}.\n' \
              'See vm create -h for more information on specifying an image.'
        raise CLIError(err.format(namespace.image, [x['urnAlias'] for x in images]))


    namespace.source_dict = source
    namespace.scripts_arr = scripts

def create_image_template(cmd, client, resource_group_name, location, template_name, source, scripts, checksum=None,
                          managed_image_destinations=None, shared_image_destinations=None,
                          source_dict=None, scripts_arr=None):
    pass


def _set_image_template_source(template, source, checksum=None):
    pass

def _set_image_template_customizer(template, script):
    pass

def _set_image_template_distributions(template, destination, replica_locations):
    pass