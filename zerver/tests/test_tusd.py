import os

from django.conf import settings

from zerver.lib.test_classes import ZulipTestCase
from zerver.models import Attachment, get_realm


class ZephyrTest(ZulipTestCase):
    def test_tusd_auth(self) -> None:
        body = {
            "Upload": {
                "ID": "",
            },
        }
        result = self.client_post(
            f"/tusd/hooks?secret={settings.SHARED_SECRET}",
            body,
            content_type="application/json",
            HTTP_HOOK_NAME="pre-create",
        )
        self.assert_json_error_contains(
            result, "Not logged in: API authentication or user session required", 401
        )

    def test_tusd_pre_create_hook(self) -> None:
        self.login("hamlet")
        body = {
            "Upload": {
                "ID": "",
                "IsFinal": False,
                "IsPartial": False,
                "MetaData": {
                    "filename": "jupyterlab-galata-report.zip",
                    "filetype": "application/zip",
                    "name": "jupyterlab-galata-report.zip",
                    "type": "application/zip",
                },
                "Offset": 0,
                "PartialUploads": None,
                "Size": settings.MAX_FILE_UPLOAD_SIZE * 1024 * 1024 - 100,
                "SizeIsDeferred": False,
                "Storage": None,
            },
        }
        result = self.client_post(
            f"/tusd/hooks?secret={settings.SHARED_SECRET}",
            body,
            content_type="application/json",
            HTTP_HOOK_NAME="pre-create",
        )
        self.assert_json_success(result)

    def test_file_too_big_failure(self) -> None:
        self.login("hamlet")
        body = {
            "Upload": {
                "Size": settings.MAX_FILE_UPLOAD_SIZE * 1024 * 1024 + 100,
            },
        }
        with self.settings(MAX_FILE_UPLOAD_SIZE=0):
            result = self.client_post(
                f"/tusd/hooks?secret={settings.SHARED_SECRET}",
                body,
                content_type="application/json",
                HTTP_HOOK_NAME="pre-create",
            )

        self.assert_json_error(result, "Uploaded file is larger than the allowed limit of 0 MiB")

    def test_tusd_pre_finish_hook(self) -> None:
        self.login("hamlet")
        assert settings.MAX_FILE_UPLOAD_SIZE is not None
        assert settings.LOCAL_FILES_DIR is not None
        assert settings.LOCAL_UPLOADS_DIR is not None
        file_path = os.path.join(settings.LOCAL_UPLOADS_DIR, "tusd", "xyz")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "+bw") as f:
            f.write(os.urandom(100))
            f.close()
        self.assertTrue(os.path.exists(file_path))
        body = {
            "Upload": {
                "ID": "xyz",
                "IsFinal": False,
                "IsPartial": False,
                "MetaData": {
                    "filename": "brijsiyag.zip",
                    "filetype": "application/zip",
                    "name": "brijsiyag.zip",
                    "type": "application/zip",
                },
                "Offset": 0,
                "PartialUploads": None,
                "Size": settings.MAX_FILE_UPLOAD_SIZE * 1024 * 1024 - 100,
                "SizeIsDeferred": False,
                "Storage": None,
            },
        }
        result = self.client_post(
            f"/tusd/hooks?secret={settings.SHARED_SECRET}",
            body,
            content_type="application/json",
            HTTP_HOOK_NAME="pre-finish",
        )
        self.assert_json_success(result)

        realm = get_realm("zulip")
        path_id = os.path.join(str(realm.id), "xyz", "brijsiyag.zip")
        self.assertTrue(os.path.exists(os.path.join(settings.LOCAL_FILES_DIR, path_id)))

        attachment = Attachment.objects.get(path_id=path_id)
        self.assertEqual(repr(attachment), "<Attachment: brijsiyag.zip>")

    def test_tusd_invalid_hook(self) -> None:
        self.login("hamlet")
        body = {"Upload": {"ID": "xyz"}}
        result = self.client_post(
            f"/tusd/hooks?secret={settings.SHARED_SECRET}",
            body,
            content_type="application/json",
            HTTP_HOOK_NAME="pre-xyz",
        )
        self.assert_json_error(result, "Unexpected hook.")
