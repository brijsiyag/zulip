from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from scripts.lib.zulip_tools import run


def set_query_parameter(url: str, param_name: str, param_value: str) -> str:
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)
    query_params[param_name] = [param_value]
    new_query_string = urlencode(query_params, doseq=True)

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


class Command(BaseCommand):
    help = """Starts the TusD Server"""

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("port", help="[Port to bind HTTP server to]", type=int)
        parser.add_argument(
            "hooks_http", help="[An HTTP endpoint to which hook events will be sent to]"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        port = options["port"]
        hooks_http = options["hooks_http"]
        hooks_http = set_query_parameter(hooks_http, "secret", settings.SHARED_SECRET)
        run(
            [
                "tusd",
                f"-upload-dir={settings.LOCAL_UPLOADS_DIR}/tusd",
                f"-hooks-http={hooks_http}",
                "-base-path=/chunk-upload/",
                "--hooks-enabled-events=pre-create,pre-finish",
                f"-port={port}",
                "-host=127.0.0.1",
                "-hooks-http-forward-headers=Cookie,X-Csrftoken,User-Agent,Authorization",
                "-behind-proxy",
                "-verbose",
            ]
        )
