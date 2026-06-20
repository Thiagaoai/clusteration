#!/usr/bin/env python3
"""Audit and repair the Dokploy application serving Clusteration.

This intentionally uses only the Python standard library so it can run on the
Dokploy host, inside a one-off container, or from a local shell with an API key.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


EXPECTED_BUILD = "2026-06-20-dokploy-runtime-proof-v3"
SENSITIVE_KEY_PARTS = ("secret", "password", "token", "private")
SENSITIVE_KEYS = {"env", "envs", "envvars", "environmentvariables", "buildargs", "buildsecrets"}


@dataclass
class Candidate:
    score: int
    app_id: str
    name: str
    app_name: str
    matched_domain: bool
    raw: dict[str, Any]


def load_json_url(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> Any:
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=timeout) as response:
        data = response.read()
    if not data:
        return {}
    return json.loads(data.decode("utf-8"))


def api_json(
    base_url: str,
    api_key: str,
    method: str,
    endpoint: str,
    *,
    query: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 60,
) -> Any:
    url = base_url.rstrip("/") + "/api/" + endpoint.lstrip("/")
    if query:
        url += "?" + urlencode(query)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "accept": "application/json",
        "x-api-key": api_key,
    }
    if body is not None:
        headers["content-type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"{method} {endpoint} failed HTTP {exc.code}: {detail[:600]}") from exc
    if not payload:
        return {}
    return json.loads(payload.decode("utf-8"))


def public_build(public_url: str) -> dict[str, Any]:
    url = public_url.rstrip("/") + "/version"
    try:
        payload = load_json_url(url, timeout=20)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc), "url": url}
    if not isinstance(payload, dict):
        return {"ok": False, "error": "non-object response", "url": url}
    return {"ok": True, "url": url, **payload}


def walk_dicts(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(walk_dicts(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(walk_dicts(child))
    return found


def as_text(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=True).lower()


def collect_candidates(projects: Any, app_name: str, domain: str) -> list[Candidate]:
    candidates: list[Candidate] = []
    app_name_l = app_name.lower()
    domain_l = domain.lower()
    seen: set[str] = set()
    for item in walk_dicts(projects):
        app_id = str(item.get("applicationId") or item.get("appId") or "").strip()
        name = str(item.get("name") or "").strip()
        dokploy_app_name = str(item.get("appName") or "").strip()
        if not app_id and not dokploy_app_name:
            continue
        blob = as_text(item)
        matched_domain = bool(domain_l and domain_l in blob)
        score = 0
        if app_id:
            score += 2
        if app_name_l and app_name_l in name.lower():
            score += 8
        if app_name_l and app_name_l in dokploy_app_name.lower():
            score += 8
        if app_name_l and app_name_l in blob:
            score += 4
        if matched_domain:
            score += 10
        if score < 6:
            continue
        key = app_id or dokploy_app_name
        if key in seen:
            continue
        seen.add(key)
        candidates.append(Candidate(score, app_id, name, dokploy_app_name, matched_domain, item))
    return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, child in value.items():
            key_l = str(key).lower()
            if key_l in SENSITIVE_KEYS or any(part in key_l for part in SENSITIVE_KEY_PARTS):
                redacted[key] = "<redacted>"
            else:
                redacted[key] = redact(child)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value[:20]]
    return value


def print_json(label: str, value: Any) -> None:
    print(f"\n== {label} ==")
    text = json.dumps(redact(value), indent=2, ensure_ascii=False, default=str)
    print(text[:12000])


def pick_application(
    base_url: str,
    api_key: str,
    explicit_app_id: str,
    app_name: str,
    domain: str,
) -> tuple[str, str, list[Candidate]]:
    if explicit_app_id:
        return explicit_app_id, app_name, []
    projects = api_json(base_url, api_key, "GET", "project.all")
    candidates = collect_candidates(projects, app_name, domain)
    if not candidates:
        print_json("project.all", projects)
        raise RuntimeError(f"no Dokploy application matched app={app_name!r} domain={domain!r}")
    print("\n== Dokploy candidates ==")
    for candidate in candidates:
        print(
            f"score={candidate.score} id={candidate.app_id or '-'} "
            f"name={candidate.name or '-'} appName={candidate.app_name or '-'} "
            f"domain={'yes' if candidate.matched_domain else 'no'}"
        )
    top = candidates[0]
    if len(candidates) > 1 and top.score == candidates[1].score:
        raise RuntimeError("multiple Dokploy applications matched; rerun with --app-id")
    if not top.app_id:
        raise RuntimeError("matched application has no applicationId; rerun with --app-id")
    return top.app_id, top.app_name or top.name or app_name, candidates


def wait_for_expected_build(public_url: str, expected_build: str, timeout_seconds: int) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while True:
        status = public_build(public_url)
        print_json("public /version", status)
        if status.get("build") == expected_build:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(5)


def read_application_logs(base_url: str, api_key: str, app_id: str, tail: int = 300) -> str:
    logs = api_json(
        base_url,
        api_key,
        "GET",
        "application.readLogs",
        query={"applicationId": app_id, "tail": str(tail), "since": "all"},
    )
    if isinstance(logs, str):
        return logs
    if isinstance(logs, dict):
        for key in ("logs", "log", "message", "data"):
            value = logs.get(key)
            if isinstance(value, str):
                return value
        return json.dumps(redact(logs), ensure_ascii=False, default=str)
    return json.dumps(redact(logs), ensure_ascii=False, default=str)


def print_runtime_log_summary(logs: str, expected_build: str) -> None:
    print("\n== application.readLogs runtime proof ==")
    lines = logs.splitlines()
    matches = [
        line
        for line in lines
        if "CLUSTERATION_RUNTIME" in line or expected_build in line or "Application startup failed" in line
    ]
    if matches:
        for line in matches[-20:]:
            print(line)
        return
    print("No CLUSTERATION_RUNTIME marker found in the latest application logs.")
    for line in lines[-40:]:
        print(line)


def run() -> int:
    parser = argparse.ArgumentParser(description="Audit and repair Clusteration on Dokploy")
    parser.add_argument("--dokploy-url", default=os.getenv("DOKPLOY_URL", "http://23.25.234.77:3000"))
    parser.add_argument("--api-key", default=os.getenv("DOKPLOY_API_KEY", ""))
    parser.add_argument("--app-id", default=os.getenv("DOKPLOY_APPLICATION_ID", ""))
    parser.add_argument("--app-name", default=os.getenv("DOKPLOY_APP_NAME", "clusteration"))
    parser.add_argument("--domain", default=os.getenv("CLUSTERATION_DOMAIN", "app.thiagao.online"))
    parser.add_argument("--public-url", default=os.getenv("CLUSTERATION_PUBLIC_URL", "https://app.thiagao.online"))
    parser.add_argument("--expected-build", default=os.getenv("EXPECTED_BUILD", EXPECTED_BUILD))
    parser.add_argument("--repair", action="store_true", help="run reload/redeploy for the selected application")
    parser.add_argument("--restart", action="store_true", help="stop/start the selected application after redeploy")
    parser.add_argument(
        "--deploy-method",
        choices=("deploy", "redeploy", "both"),
        default=os.getenv("DOKPLOY_DEPLOY_METHOD", "deploy"),
        help="Dokploy endpoint to trigger after reload",
    )
    parser.add_argument("--clean-queues", action="store_true", help="cancel pending Dokploy queues before repair")
    parser.add_argument("--logs", action="store_true", help="print runtime proof from application logs")
    parser.add_argument("--wait", type=int, default=180, help="seconds to wait for public /version after repair")
    args = parser.parse_args()

    status = public_build(args.public_url)
    print_json("public /version before", status)

    if not args.api_key:
        if status.get("build") == args.expected_build:
            return 0
        print("\nDOKPLOY_API_KEY is required to inspect/reload the active Dokploy application.")
        print("Create it in Dokploy profile API/CLI settings, then export DOKPLOY_API_KEY and rerun.")
        return 2

    app_id, resolved_app_name, _ = pick_application(
        args.dokploy_url,
        args.api_key,
        args.app_id,
        args.app_name,
        args.domain,
    )
    app = api_json(args.dokploy_url, args.api_key, "GET", "application.one", query={"applicationId": app_id})
    print_json("application.one", app)

    try:
        deployments = api_json(
            args.dokploy_url,
            args.api_key,
            "GET",
            "deployment.allByType",
            query={"id": app_id, "type": "application"},
        )
        print_json("deployment.allByType", deployments)
    except RuntimeError as exc:
        print(f"\nWARN deployment audit failed: {exc}")

    try:
        traefik = api_json(
            args.dokploy_url,
            args.api_key,
            "GET",
            "application.readTraefikConfig",
            query={"applicationId": app_id},
        )
        print_json("application.readTraefikConfig", traefik)
    except RuntimeError as exc:
        print(f"\nWARN traefik audit failed: {exc}")

    if args.logs:
        try:
            print_runtime_log_summary(read_application_logs(args.dokploy_url, args.api_key, app_id), args.expected_build)
        except RuntimeError as exc:
            print(f"\nWARN application log read failed: {exc}")

    if not args.repair:
        return 0 if status.get("build") == args.expected_build else 3

    print(f"\n== repair applicationId={app_id} appName={resolved_app_name} ==")
    if args.clean_queues:
        api_json(args.dokploy_url, args.api_key, "POST", "application.cleanQueues", body={"applicationId": app_id})
    api_json(
        args.dokploy_url,
        args.api_key,
        "POST",
        "application.reload",
        body={"applicationId": app_id, "appName": resolved_app_name},
    )
    if args.restart:
        api_json(args.dokploy_url, args.api_key, "POST", "application.stop", body={"applicationId": app_id})
        time.sleep(5)

    if args.deploy_method in ("deploy", "both"):
        api_json(args.dokploy_url, args.api_key, "POST", "application.deploy", body={"applicationId": app_id})
    if args.deploy_method in ("redeploy", "both"):
        api_json(
            args.dokploy_url,
            args.api_key,
            "POST",
            "application.redeploy",
            body={
                "applicationId": app_id,
                "title": "Runtime repair",
                "description": f"Force current Clusteration build {args.expected_build}",
            },
        )
    if args.restart:
        api_json(args.dokploy_url, args.api_key, "POST", "application.start", body={"applicationId": app_id})

    ok = wait_for_expected_build(args.public_url, args.expected_build, args.wait)
    try:
        print_runtime_log_summary(read_application_logs(args.dokploy_url, args.api_key, app_id), args.expected_build)
    except RuntimeError as exc:
        print(f"\nWARN application log read failed: {exc}")
    return 0 if ok else 4


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except (RuntimeError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        raise SystemExit(1)
