import os
import random
import secrets

from shutil import move
from typing import Any, Dict, Mapping

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext as _

from zerver.decorator import internal_notify_view
from zerver.lib.exceptions import JsonableError
from zerver.lib.request import REQ, has_request_variables
from zerver.lib.response import json_success
from zerver.lib.upload import check_upload_within_quota
from zerver.lib.upload.base import create_attachment, sanitize_name
from zerver.models import Realm, UserProfile


def generate_path(realm_id: str, file_id: str, uploaded_file_name: str) -> str:
    # Split into 256 subdirectories to prevent directories from getting too big
    return "/".join(
        [
            realm_id,
            format(random.randint(0, 255), "x"),
            file_id,
            sanitize_name(uploaded_file_name),
        ]
    )


def move_file(file_id: str, path_id: str) -> None:
    assert settings.LOCAL_FILES_DIR is not None
    assert settings.LOCAL_UPLOADS_DIR is not None
    file_path = os.path.join(settings.LOCAL_FILES_DIR, path_id)
    current_path = os.path.join(settings.LOCAL_UPLOADS_DIR, "tusd", file_id)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    move(current_path, file_path)


def handle_pre_create_hook(
    request: HttpRequest, user_profile: UserProfile, data: Dict[str, Any]
) -> HttpResponse:
    file_size = data["Size"]
    assert file_size != 0
    if settings.MAX_FILE_UPLOAD_SIZE * 1024 * 1024 < file_size:
        raise JsonableError(
            _("Uploaded file is larger than the allowed limit of {} MiB").format(
                settings.MAX_FILE_UPLOAD_SIZE,
            )
        )
    check_upload_within_quota(user_profile.realm, file_size)
    return json_success(request)


def handle_pre_finish_hook(
    request: HttpRequest, user_profile: UserProfile, data: Dict[str, Any]
) -> HttpResponse:
    file_id = data["ID"]
    realm = user_profile.realm

    file_name = data["MetaData"]["filename"]
    file_size = data["Size"]
    path_id = generate_path(str(realm.id), file_id, file_name)

    move_file(file_id, path_id)

    create_attachment(file_name, path_id, user_profile, realm, file_size, file_id=file_id)

    return json_success(request)


@internal_notify_view(False)
@has_request_variables
def handle_tusd_hook(
    request: HttpRequest,
    user_profile: UserProfile,
    payload: Mapping[str, Any] = REQ(argument_type="body"),
) -> HttpResponse:
    hook_name = request.META.get("HTTP_HOOK_NAME")
    body = payload["Upload"]
    if hook_name == "pre-create":
        return handle_pre_create_hook(request, user_profile, body)
    if hook_name == "pre-finish":
        return handle_pre_finish_hook(request, user_profile, body)
    raise JsonableError(_("Unexpected hook."))
