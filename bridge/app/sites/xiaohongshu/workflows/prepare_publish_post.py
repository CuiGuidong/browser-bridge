import time


PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official"


def _wait_for_target_stable(browser_runtime, target_id, timeout_seconds=8, interval_seconds=0.4):
    if not target_id:
        return None
    try:
        return browser_runtime.wait_for_page(
            target_id=target_id,
            timeout_seconds=timeout_seconds,
            interval_seconds=interval_seconds,
        )
    except Exception:
        return None


def _normalize_image_paths(params):
    params = params or {}
    values = []
    for key in ("imagePath", "imagePaths", "images", "files"):
        raw = params.get(key)
        if not raw:
            continue
        if isinstance(raw, str):
            values.append(raw)
            continue
        if isinstance(raw, (list, tuple)):
            values.extend(raw)
    normalized = []
    seen = set()
    for value in values:
        path = str(value or "").strip()
        if not path or path in seen:
            continue
        normalized.append(path)
        seen.add(path)
    return normalized


def _open_creator_page(browser_runtime, target_id=None):
    opened = None
    resolved_target_id = target_id
    if resolved_target_id:
        opened = browser_runtime.navigate_tab(resolved_target_id, PUBLISH_URL)
        if not opened:
            return None, None
        resolved_target_id = opened.get("targetId") or opened.get("id") or target_id
    else:
        opened = browser_runtime.open_or_reuse_url(
            PUBLISH_URL,
            reuse_existing_tab=False,
            reuse_domain="xiaohongshu.com",
        )
        if not opened:
            return None, None
        resolved_target_id = opened.get("targetId") or opened.get("id") or target_id
    _wait_for_target_stable(browser_runtime, resolved_target_id)
    return resolved_target_id, opened


def _read_publish_state(read_service, target_id, timeout_seconds=20):
    return read_service.site_read(
        site="xiaohongshu",
        kind="read_creator_publish_state",
        params={
            "waitForReady": True,
            "intervalSeconds": 0.5,
        },
        target_id=target_id,
        timeout_seconds=timeout_seconds,
    )


def _wait_for_editor_page(read_service, target_id, timeout_seconds=20, interval_seconds=0.8, stable_rounds=2):
    started = time.time()
    last_state = None
    stable_hits = 0
    while time.time() - started < timeout_seconds:
        last_state = _read_publish_state(
            read_service=read_service,
            target_id=target_id,
            timeout_seconds=min(6, timeout_seconds),
        )
        content = (last_state or {}).get("content") or {}
        if last_state and last_state.get("ok") and content.get("pageType") == "creator_publish_editor_image":
            stable_hits += 1
            if stable_hits >= stable_rounds:
                return last_state
        else:
            stable_hits = 0
        time.sleep(interval_seconds)
    return last_state


def _wait_for_image_flow(read_service, target_id, timeout_seconds=12, interval_seconds=0.6):
    started = time.time()
    last_state = None
    while time.time() - started < timeout_seconds:
        last_state = _read_publish_state(
            read_service=read_service,
            target_id=target_id,
            timeout_seconds=min(6, timeout_seconds),
        )
        content = (last_state or {}).get("content") or {}
        if content.get("pageType") == "creator_publish_editor_image":
            return last_state
        if content.get("activeTab") == "image":
            return last_state
        image_upload = content.get("imageUpload") or {}
        if image_upload.get("exists"):
            return last_state
        time.sleep(interval_seconds)
    return last_state


def _action_error(site, workflow, error, target_id, debug=None):
    return {
        "ok": False,
        "site": site,
        "workflow": workflow,
        "targetId": target_id,
        "error": error,
        "debug": debug or {},
    }


def _refresh_fill_result(read_service, target_id, field, expected_text, timeout_seconds=8, interval_seconds=0.6):
    started = time.time()
    last_state = None
    while time.time() - started < timeout_seconds:
        last_state = _read_publish_state(
            read_service=read_service,
            target_id=target_id,
            timeout_seconds=min(6, timeout_seconds),
        )
        content = (last_state or {}).get("content") or {}
        if field == "title":
            current = ((content.get("titleInput") or {}).get("value") or "").strip()
            if current == expected_text:
                return {
                    "ok": True,
                    "verified": True,
                    "after": {
                        "value": current,
                        "length": len(current),
                    },
                    "state": last_state,
                }
        elif field == "content":
            current = ((content.get("contentEditor") or {}).get("text") or "").strip()
            if current == expected_text:
                return {
                    "ok": True,
                    "verified": True,
                    "after": {
                        "text": current,
                        "length": len(current),
                    },
                    "state": last_state,
                }
        time.sleep(interval_seconds)
    return {
        "ok": False,
        "verified": False,
        "state": last_state,
    }


def run(action_service, read_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    title = str((params or {}).get("title") or "").strip()
    content = str((params or {}).get("content") or "").strip()
    image_paths = _normalize_image_paths(params)

    if not title:
        return _action_error("xiaohongshu", "prepare_publish_post", "title is required", target_id)
    if not content:
        return _action_error("xiaohongshu", "prepare_publish_post", "content is required", target_id)
    if not image_paths:
        return _action_error("xiaohongshu", "prepare_publish_post", "image path is required", target_id)

    resolved_target_id, opened = _open_creator_page(browser_runtime, target_id=target_id)
    if not resolved_target_id:
        return _action_error("xiaohongshu", "prepare_publish_post", "failed to open page", target_id)

    initial_state = _read_publish_state(
        read_service=read_service,
        target_id=resolved_target_id,
        timeout_seconds=timeout_seconds,
    )
    if not initial_state or initial_state.get("ok") is False:
        return {
            **(initial_state or {}),
            "site": "xiaohongshu",
            "workflow": "prepare_publish_post",
            "targetId": resolved_target_id,
            "debug": {
                "open": opened,
                **((initial_state or {}).get("debug") or {}),
            },
        }

    working_state = initial_state
    working_content = working_state.get("content") or {}
    if working_content.get("pageType") == "creator_publish_entry" and working_content.get("activeTab") != "image":
        switch_result = action_service.site_action(
            "xiaohongshu",
            "switch_creator_tab",
            params={"tab": "image"},
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        if not switch_result or switch_result.get("ok") is False:
            return {
                **(switch_result or {}),
                "site": "xiaohongshu",
                "workflow": "prepare_publish_post",
                "targetId": resolved_target_id,
                "debug": {
                    "open": opened,
                    "initialState": initial_state,
                    **((switch_result or {}).get("debug") or {}),
                },
            }
        working_state = _wait_for_image_flow(
            read_service=read_service,
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        working_content = (working_state or {}).get("content") or {}
        if not working_state or working_state.get("ok") is False:
            return {
                **(working_state or {}),
                "site": "xiaohongshu",
                "workflow": "prepare_publish_post",
                "targetId": resolved_target_id,
                "debug": {
                    "open": opened,
                    "initialState": initial_state,
                    "switchResult": switch_result,
                    **((working_state or {}).get("debug") or {}),
                },
            }
        image_upload = working_content.get("imageUpload") or {}
        if working_content.get("pageType") != "creator_publish_editor_image" and not image_upload.get("exists"):
            return _action_error(
                "xiaohongshu",
                "prepare_publish_post",
                "failed to switch to image flow",
                resolved_target_id,
                debug={
                    "open": opened,
                    "initialState": initial_state,
                    "switchResult": switch_result,
                    "workingState": working_state,
                },
            )

    if working_content.get("pageType") == "creator_publish_entry":
        locate_result = action_service.site_action(
            "xiaohongshu",
            "locate_creator_image_file_input",
            params={},
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        selector = (locate_result or {}).get("selector") or (((locate_result or {}).get("after") or {}).get("selector"))
        if not selector or locate_result.get("ok") is False or not locate_result.get("verified"):
            return {
                **(locate_result or {}),
                "site": "xiaohongshu",
                "workflow": "prepare_publish_post",
                "targetId": resolved_target_id,
                "debug": {
                    "open": opened,
                    "initialState": initial_state,
                    "workingState": working_state,
                    **((locate_result or {}).get("debug") or {}),
                },
            }
        upload_result = browser_runtime.set_file_input_files_by_selector(
            target_id=resolved_target_id,
            selector=selector,
            files=image_paths,
        )
        if not upload_result or upload_result.get("ok") is False:
            return {
                **(upload_result or {}),
                "site": "xiaohongshu",
                "workflow": "prepare_publish_post",
                "targetId": resolved_target_id,
                "debug": {
                    "open": opened,
                    "selector": selector,
                    "initialState": initial_state,
                    "workingState": working_state,
                    **((upload_result or {}).get("debug") or {}),
                },
            }
        working_state = _wait_for_editor_page(
            read_service=read_service,
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        working_content = (working_state or {}).get("content") or {}
        if not working_state or working_state.get("ok") is False or working_content.get("pageType") != "creator_publish_editor_image":
            return {
                **(working_state or {}),
                "ok": False,
                "site": "xiaohongshu",
                "workflow": "prepare_publish_post",
                "targetId": resolved_target_id,
                "error": "failed to enter image editor page",
                "debug": {
                    "open": opened,
                    "upload": upload_result,
                    "initialState": initial_state,
                    **((working_state or {}).get("debug") or {}),
                },
            }
    elif working_content.get("pageType") != "creator_publish_editor_image":
        return _action_error(
            "xiaohongshu",
            "prepare_publish_post",
            "unexpected creator publish page type",
            resolved_target_id,
            debug={
                "open": opened,
                "initialState": initial_state,
                "workingState": working_state,
            },
        )

    working_state = _wait_for_editor_page(
        read_service=read_service,
        target_id=resolved_target_id,
        timeout_seconds=min(timeout_seconds, 12),
        interval_seconds=0.6,
        stable_rounds=2,
    )

    title_result = action_service.site_action(
        "xiaohongshu",
        "fill_creator_title",
        params={"text": title},
        target_id=resolved_target_id,
        timeout_seconds=timeout_seconds,
    )
    if (
        title_result
        and title_result.get("ok") is False
        and title_result.get("error") == "creator title input not found"
    ):
        working_state = _wait_for_editor_page(
            read_service=read_service,
            target_id=resolved_target_id,
            timeout_seconds=min(timeout_seconds, 10),
            interval_seconds=0.6,
            stable_rounds=2,
        )
        title_result = action_service.site_action(
            "xiaohongshu",
            "fill_creator_title",
            params={"text": title},
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
    if title_result and title_result.get("ok") and not title_result.get("verified"):
        refreshed = _refresh_fill_result(
            read_service=read_service,
            target_id=resolved_target_id,
            field="title",
            expected_text=title,
            timeout_seconds=min(timeout_seconds, 8),
        )
        if refreshed.get("verified"):
            title_result["verified"] = True
            title_result["after"] = refreshed.get("after") or {}
            title_result.setdefault("debug", {})
            title_result["debug"]["postReadVerify"] = refreshed.get("state")
    if not title_result or title_result.get("ok") is False or not title_result.get("verified"):
        return {
            **(title_result or {}),
            "site": "xiaohongshu",
            "workflow": "prepare_publish_post",
            "targetId": resolved_target_id,
            "debug": {
                "open": opened,
                "stateBeforeFill": working_state,
                **((title_result or {}).get("debug") or {}),
            },
        }

    content_result = action_service.site_action(
        "xiaohongshu",
        "fill_creator_content",
        params={"text": content},
        target_id=resolved_target_id,
        timeout_seconds=timeout_seconds,
    )
    if (
        content_result
        and content_result.get("ok") is False
        and content_result.get("error") == "creator content editor not found"
    ):
        working_state = _wait_for_editor_page(
            read_service=read_service,
            target_id=resolved_target_id,
            timeout_seconds=min(timeout_seconds, 10),
            interval_seconds=0.6,
            stable_rounds=2,
        )
        content_result = action_service.site_action(
            "xiaohongshu",
            "fill_creator_content",
            params={"text": content},
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
    if content_result and content_result.get("ok") and not content_result.get("verified"):
        refreshed = _refresh_fill_result(
            read_service=read_service,
            target_id=resolved_target_id,
            field="content",
            expected_text=content,
            timeout_seconds=min(timeout_seconds, 8),
        )
        if refreshed.get("verified"):
            content_result["verified"] = True
            content_result["after"] = refreshed.get("after") or {}
            content_result.setdefault("debug", {})
            content_result["debug"]["postReadVerify"] = refreshed.get("state")
    if not content_result or content_result.get("ok") is False or not content_result.get("verified"):
        return {
            **(content_result or {}),
            "site": "xiaohongshu",
            "workflow": "prepare_publish_post",
            "targetId": resolved_target_id,
            "debug": {
                "open": opened,
                "titleResult": title_result,
                **((content_result or {}).get("debug") or {}),
            },
        }

    final_check = action_service.site_action(
        "xiaohongshu",
        "assert_ready_before_publish",
        params={},
        target_id=resolved_target_id,
        timeout_seconds=timeout_seconds,
    )
    if not final_check or final_check.get("ok") is False or not final_check.get("verified"):
        return {
            **(final_check or {}),
            "site": "xiaohongshu",
            "workflow": "prepare_publish_post",
            "targetId": resolved_target_id,
            "debug": {
                "open": opened,
                "titleResult": title_result,
                "contentResult": content_result,
                **((final_check or {}).get("debug") or {}),
            },
        }

    final_state = _read_publish_state(
        read_service=read_service,
        target_id=resolved_target_id,
        timeout_seconds=timeout_seconds,
    )
    final_content = (final_state or {}).get("content") or {}

    return {
        "ok": True,
        "site": "xiaohongshu",
        "workflow": "prepare_publish_post",
        "targetId": resolved_target_id,
        "summary": {
            "pageType": final_content.get("pageType"),
            "activeTab": final_content.get("activeTab"),
            "imageCount": len(image_paths),
            "keptOpenForManualPublish": True,
        },
        "items": [],
        "checkpoint": {
            "awaitingManualPublish": True,
        },
        "page": (final_state or {}).get("page") or {},
        "signals": (final_state or {}).get("signals") or {},
        "content": final_content,
        "debug": {
            "open": opened,
            "initialState": initial_state,
            "titleResult": title_result,
            "contentResult": content_result,
            "finalCheck": final_check,
        },
    }
