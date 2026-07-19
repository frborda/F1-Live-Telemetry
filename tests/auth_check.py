"""Pruebas del login F1TV del capturador, sin red ni navegador: extracción
del token desde lo que el usuario pegue, y que el servidor de auth manda el
header de Private/Local Network Access que Chrome 130+ exige.

Uso:  python tests/auth_check.py
"""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from http.server import HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.stdout.reconfigure(errors="replace")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_TMP = tempfile.mkdtemp(prefix="f1telem-auth-test-")
os.environ["APPDATA"] = _TMP
os.environ["LOCALAPPDATA"] = _TMP

from f1telem.capture_app import (
    _pna_handler, extract_subscription_token, register_protocol,
    token_from_url,
)
from fastf1.internals import f1auth

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"[{'OK ' if cond else 'FAIL'}] {msg}", flush=True)
    if not cond:
        FAILURES.append(msg)


# ------------------------------------------------- extracción de token

JWT = "ey" + "J0eXAiOiJKV1QifQ" + "." + "eyJzdWIiOiIxIn0" + "." + "sig_part_xyz"
cookie_obj = {"data": {"subscriptionToken": JWT}}
cookie_json = json.dumps(cookie_obj)
cookie_encoded = urllib.parse.quote(cookie_json)

check(extract_subscription_token(cookie_json) == JWT,
      "token: cookie JSON cruda")
check(extract_subscription_token(cookie_encoded) == JWT,
      "token: cookie URL-encodeada (como la manda la extensión)")
check(extract_subscription_token(f'"{cookie_encoded}"') == JWT,
      "token: cookie entre comillas (copy/paste)")
check(extract_subscription_token(JWT) == JWT, "token: JWT pelado")
check(extract_subscription_token(f'  {JWT}  ') == JWT, "token: JWT con espacios")
check(extract_subscription_token('{"subscriptionToken": "%s"}' % JWT) == JWT,
      "token: JSON sin envoltorio 'data'")
check(extract_subscription_token("") is None, "token: vacío -> None")
check(extract_subscription_token("hola mundo") is None, "token: basura -> None")
check(extract_subscription_token("{not json") is None, "token: JSON roto -> None")

# ------------------------------------------------- enlace f1telemetry://

check(token_from_url(f"f1telemetry://auth?token={urllib.parse.quote(JWT)}") == JWT,
      "protocolo: token en query URL-encodeado")
check(token_from_url(f"f1telemetry://auth?token={JWT}") == JWT,
      "protocolo: token en query crudo")
check(token_from_url(f"f1telemetry://{JWT}") == JWT,
      "protocolo: token como ruta")
check(token_from_url("f1telemetry://auth?token=basura") is None,
      "protocolo: basura -> None")
register_protocol()  # sin build congelado no debe tocar el registro ni fallar
check(True, "protocolo: register_protocol es no-op sin build congelado")

# ------------------------------------------------- header PNA del servidor

Handler = _pna_handler(f1auth.AuthHandler)
httpd = HTTPServer(("127.0.0.1", 0), Handler)
port = httpd.server_port
threading.Thread(target=httpd.serve_forever, daemon=True).start()

# ::1 en el mismo puerto (localhost en Windows resuelve a IPv6 primero)
v6_ok = False
try:
    class _V6(HTTPServer):
        address_family = socket.AF_INET6
    httpd6 = _V6(("::1", port), Handler)
    threading.Thread(target=httpd6.serve_forever, daemon=True).start()
    v6_ok = True
except OSError:
    pass
time.sleep(0.3)


def options(host: str):
    req = urllib.request.Request(
        f"http://{host}:{port}/auth", method="OPTIONS",
        headers={"Origin": "https://f1login.fastf1.dev",
                 "Access-Control-Request-Private-Network": "true"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return {k.lower(): v for k, v in resp.headers.items()}, resp.status


headers, status = options("127.0.0.1")
check(status == 200, f"preflight IPv4 responde 200 ({status})")
check(headers.get("access-control-allow-private-network") == "true",
      "preflight trae Access-Control-Allow-Private-Network: true")
check(headers.get("access-control-allow-origin") == "*",
      "preflight conserva el CORS de FastF1")

if v6_ok:
    h6, s6 = options("[::1]")
    check(s6 == 200 and h6.get("access-control-allow-private-network") == "true",
          "preflight IPv6 (::1) también trae el header PNA")
else:
    check(True, "IPv6 no disponible en este host (se omite)")

# el handler base de FastF1 NO manda el header (regresión que arreglamos)
plain = HTTPServer(("127.0.0.1", 0), f1auth.AuthHandler)
pport = plain.server_port
threading.Thread(target=plain.serve_forever, daemon=True).start()
time.sleep(0.2)
req = urllib.request.Request(f"http://127.0.0.1:{pport}/auth", method="OPTIONS")
with urllib.request.urlopen(req, timeout=5) as resp:
    base_headers = {k.lower(): v for k, v in resp.headers.items()}
check("access-control-allow-private-network" not in base_headers,
      "el handler base de FastF1 no manda el header (por eso fallaba)")

# ------------------------------------------------- extensión de Chrome

EXT = Path(__file__).resolve().parents[1] / "extension"
manifest = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))
check(manifest["manifest_version"] == 3, "extensión: manifest v3")
check(set(manifest["permissions"]) >= {"cookies", "storage"},
      "extensión: permisos de cookies y storage")
hosts = " ".join(manifest["host_permissions"])
check("localhost" in hosts and "formula1.com" in hosts and "fastf1.dev" in hosts,
      "extensión: host_permissions para localhost, F1 y fastf1.dev")
check((EXT / manifest["background"]["service_worker"]).exists(),
      "extensión: service worker presente")
check((EXT / "icon.png").exists() and (EXT / "connect.html").exists(),
      "extensión: icon y connect.html presentes")

connect_js = (EXT / "connect.js").read_text(encoding="utf-8")
check('targetAddressSpace: "loopback"' in connect_js,
      "extensión: fetch declara targetAddressSpace loopback (fix Chrome 130+)")
check("/auth" in connect_js and "loginSession" in connect_js,
      "extensión: postea loginSession a /auth (protocolo FastF1)")
check("subscriptionToken" in connect_js and "Paste token" in connect_js,
      "extensión: plan B con token copiable para Paste token…")
check("f1telemetry://auth?token=" in connect_js,
      "extensión: botón Open in the app usa el protocolo f1telemetry://")
connect_html = (EXT / "connect.html").read_text(encoding="utf-8")
check('id="openapp"' in connect_html, "extensión: botón openapp presente")

background_js = (EXT / "background.js").read_text(encoding="utf-8")
check("f1login.fastf1.dev" in background_js and "my-account" in background_js,
      "extensión: intercepta el disparador de la app y el fin del login")
check("login-session" in background_js and "livetiming.formula1.com" in background_js,
      "extensión: lee la cookie login-session")

print()
if FAILURES:
    print(f"{len(FAILURES)} FALLA(S)")
    raise SystemExit(1)
print("Todo OK")
