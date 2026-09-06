#!/usr/bin/env python3
"""
Publish an already-rendered image + caption to Instagram via the official
Graph API (graph.instagram.com). No browser automation anywhere in this file.

Usage: python3 publish.py <image_raw_url> <caption_file>
Requires env vars: IG_ACCESS_TOKEN, IG_USER_ID
"""
import os
import sys
import time
import requests

GRAPH = "https://graph.instagram.com/v21.0"


def _raise_with_body(r):
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        print(f"Graph API error response: {r.status_code} {r.text}", file=sys.stderr)
        raise


def create_container(ig_user_id, token, image_url, caption):
    r = requests.post(f"{GRAPH}/{ig_user_id}/media", data={
        "image_url": image_url,
        "caption": caption,
        "access_token": token,
    }, timeout=30)
    _raise_with_body(r)
    return r.json()["id"]


def wait_until_ready(creation_id, token, attempts=10, delay=3):
    for _ in range(attempts):
        r = requests.get(f"{GRAPH}/{creation_id}", params={
            "fields": "status_code",
            "access_token": token,
        }, timeout=30)
        _raise_with_body(r)
        status = r.json().get("status_code")
        if status == "FINISHED":
            return True
        if status == "ERROR":
            raise RuntimeError(f"container {creation_id} failed to process")
        time.sleep(delay)
    return False


def publish_container(ig_user_id, token, creation_id):
    r = requests.post(f"{GRAPH}/{ig_user_id}/media_publish", data={
        "creation_id": creation_id,
        "access_token": token,
    }, timeout=30)
    _raise_with_body(r)
    return r.json()["id"]


def main():
    image_url = sys.argv[1]
    caption_file = sys.argv[2]
    with open(caption_file, "r", encoding="utf-8") as f:
        caption = f.read()

    token = os.environ["IG_ACCESS_TOKEN"]
    ig_user_id = os.environ["IG_USER_ID"]

    creation_id = create_container(ig_user_id, token, image_url, caption)
    print(f"created container {creation_id}")
    wait_until_ready(creation_id, token)
    media_id = publish_container(ig_user_id, token, creation_id)
    print(f"published media {media_id}")


if __name__ == "__main__":
    main()
