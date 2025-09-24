import base64
import hashlib
import hmac
import json
import os

import boto3

SNS = boto3.client("sns")
TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]        # SNS topic ARN for alerts
SECRET = os.environ["WEBHOOK_SECRET"]  # same as GitHub webhook secret


def _normalize_headers(headers):
    normalized = {}
    for key, value in (headers or {}).items():
        if isinstance(key, str):
            normalized[key.lower()] = value
    return normalized



def _verify(headers, body_bytes):
    signature = headers.get("x-hub-signature-256")
    if not signature:
        return False
    expected = "sha256=" + hmac.new(SECRET.encode(), body_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)



def _publish(subject, body):
    subject_text = subject[:100] if subject else "GitHub status check failed"
    SNS.publish(TopicArn=TOPIC_ARN, Subject=subject_text, Message=body)



def _format_repo_sha(payload):
    repo = payload["repository"]["full_name"]
    url_repo = payload["repository"]["html_url"]
    sha = (payload.get("check_run") or payload.get("commit") or {}).get("sha") or payload.get("check_run", {}).get("head_sha") or ""
    short = sha[:7] if sha else ""
    return repo, url_repo, short



def handler(event, context):
    headers = _normalize_headers(event.get("headers"))
    raw_body = event.get("body", "") or ""

    if isinstance(raw_body, bytes):
        body_bytes = raw_body
    elif event.get("isBase64Encoded"):
        body_bytes = base64.b64decode(raw_body)
    else:
        body_bytes = raw_body.encode("utf-8")

    if not _verify(headers, body_bytes):
        return {"statusCode": 401, "body": "bad signature"}

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": "invalid payload"}

    etype = headers.get("x-github-event", "")

    # --- A) Checks API path (preferred) ---
    if etype == "check_run" and payload.get("action") == "completed":
        cr = payload["check_run"]
        name = cr.get("name", "")
        conclusion = cr.get("conclusion", "")
        if name == "ci/jenkins/build-status" and conclusion in {"failure", "timed_out", "cancelled"}:
            repo, url_repo, short = _format_repo_sha(payload)
            pr_url = cr.get("pull_requests", [{}])[0].get("html_url") if cr.get("pull_requests") else None
            details = cr.get("html_url")
            subject = f"[{repo}] {name} FAILED ({short})"
            body_txt = f"""Check: {name}
Repo: {repo}
Conclusion: {conclusion}
Details: {details}
Context: {pr_url or (url_repo + '/commit/' + cr.get('head_sha',''))}
"""
            _publish(subject, body_txt)

    # --- B) Legacy commit status path ---
    elif etype == "status":
        # status payload uses 'context' + 'state'
        if payload.get("context") == "ci/jenkins/build-status" and payload.get("state") == "failure":
            repo, url_repo, short = _format_repo_sha(payload)
            target = payload.get("target_url")
            subject = f"[{repo}] ci/jenkins/build-status FAILED ({short})"
            body_txt = f"""Context: ci/jenkins/build-status
Repo: {repo}
State: failure
Details: {target}
Commit: {url_repo}/commit/{payload.get('sha','')}
"""
            _publish(subject, body_txt)

    return {"statusCode": 200, "body": "ok"}
