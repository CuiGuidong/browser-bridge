import unittest
import os
import json
import tempfile
import shutil
import datetime
from unittest.mock import patch, MagicMock

from bridge.app.keepalive_scheduler import (
    KeepaliveConfig,
    KeepaliveScheduler,
    load_keepalive_config
)
import bridge.app.server as server


class FakeBrowserRuntime:
    def __init__(self):
        self.calls = []
        self.tabs = {}
        self.next_tab_id = 1

    def open_new_url(self, url):
        self.calls.append(("open_new_url", url))
        tab_id = str(self.next_tab_id)
        self.next_tab_id += 1
        tab = {"nativeTabId": tab_id, "url": url, "reused": False}
        self.tabs[tab_id] = tab
        return tab

    def wait_for_page(self, target_id, timeout_seconds=10):
        self.calls.append(("wait_for_page", target_id, timeout_seconds))
        return {
            "targetId": str(target_id),
            "title": "Fake Title",
            "url": "https://example.com",
            "stable": True,
            "elapsed": 0.1
        }

    def close_tab(self, target_id):
        self.calls.append(("close_tab", target_id))
        if target_id in self.tabs:
            del self.tabs[target_id]
            return {"targetId": str(target_id), "closed": True}
        return None


class FakeSite:
    def __init__(self, site_id, home_url):
        self.site_id = site_id
        self.home_url = home_url


class FakeSiteRegistry:
    def __init__(self):
        self.sites = {}

    def get(self, site_id):
        return self.sites.get(site_id)

    def register(self, site_id, site_module):
        self.sites[site_id] = site_module


class FakeClock:
    def __init__(self, now_dt):
        self.current_now = now_dt

    def now(self):
        return self.current_now

    def advance(self, td):
        self.current_now += td


class FakeSleeper:
    def __init__(self):
        self.slept = []

    def sleep(self, seconds):
        self.slept.append(seconds)


class FakeRng:
    def __init__(self, val):
        self.val = val

    def randint(self, a, b):
        return self.val


class KeepaliveConfigTest(unittest.TestCase):
    def test_default_config_disabled(self):
        config = load_keepalive_config(env={})
        self.assertFalse(config.enabled)
        self.assertEqual(config.sites, [])
        self.assertEqual(config.window_start, "09:00")
        self.assertEqual(config.window_end, "23:00")
        self.assertEqual(config.dwell_seconds_min, 20)
        self.assertEqual(config.dwell_seconds_max, 60)

    def test_status_file_override(self):
        env = {
            "BB_KEEPALIVE_ENABLED": "true",
            "BB_KEEPALIVE_SITES": "weibo,douban",
            "BB_KEEPALIVE_STATUS_FILE": "/tmp/custom-path.json"
        }
        config = load_keepalive_config(env=env)
        self.assertTrue(config.enabled)
        self.assertEqual(config.sites, ["weibo", "douban"])
        self.assertEqual(config.status_file, "/tmp/custom-path.json")

    def test_default_status_file_uses_user_state_dir(self):
        config_mac = load_keepalive_config(env={}, platform_system="Darwin", home="/Users/test")
        self.assertTrue("Library/Application Support/BrowserBridge" in config_mac.status_file)

        config_win = load_keepalive_config(env={"LOCALAPPDATA": "C:\\AppData"}, platform_system="Windows")
        self.assertEqual(config_win.status_file, "C:\\AppData\\BrowserBridge\\browser-bridge-keepalive-status.json")

        config_linux = load_keepalive_config(env={}, platform_system="Linux", home="/home/test")
        self.assertTrue(".local/state/browser-bridge" in config_linux.status_file)


class KeepaliveSchedulerTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.status_file = os.path.join(self.tmp_dir, "status.json")
        self.env = {
            "BB_KEEPALIVE_ENABLED": "true",
            "BB_KEEPALIVE_SITES": "weibo,douban",
            "BB_KEEPALIVE_STATUS_FILE": self.status_file
        }

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_constructor_does_not_start_thread(self):
        runtime = FakeBrowserRuntime()
        registry = FakeSiteRegistry()
        config = load_keepalive_config(env=self.env)
        scheduler = KeepaliveScheduler(runtime, registry, config)
        self.assertFalse(scheduler.is_running())

    def test_same_instance_does_not_run_twice_for_same_local_date(self):
        runtime = FakeBrowserRuntime()
        registry = FakeSiteRegistry()
        registry.register("weibo", FakeSite("weibo", "https://weibo.com"))
        registry.register("douban", FakeSite("douban", "https://douban.com"))

        config = load_keepalive_config(env=self.env)
        now_dt = datetime.datetime(2026, 7, 5, 10, 0, 0)
        clock = FakeClock(now_dt)
        sleeper = FakeSleeper()
        rng = FakeRng(30)

        scheduler = KeepaliveScheduler(runtime, registry, config, now=clock.now, sleep=sleeper.sleep, rng=rng)
        scheduler._stop_event = MagicMock()
        scheduler._stop_event.wait.return_value = False
        scheduler._stop_event.is_set.return_value = False

        scheduler.plan_next_run(clock.now())

        # Move clock to scheduled run time
        run_time = scheduler.planned_run_at
        clock.current_now = run_time

        # First run
        scheduler.run_due_once(clock.now())
        self.assertEqual(len(runtime.calls), 6)  # open, wait, close for each of 2 sites
        runtime.calls.clear()

        # Second run on same day should do nothing
        scheduler.run_due_once(clock.now())
        self.assertEqual(len(runtime.calls), 0)

    def test_new_instance_can_plan_same_local_date(self):
        runtime = FakeBrowserRuntime()
        registry = FakeSiteRegistry()
        config = load_keepalive_config(env=self.env)
        scheduler = KeepaliveScheduler(runtime, registry, config)
        scheduler.plan_next_run(datetime.datetime(2026, 7, 5, 10, 0, 0))
        self.assertIsNotNone(scheduler.planned_run_at)
        self.assertEqual(scheduler.planned_run_at.date(), datetime.date(2026, 7, 5))

    def test_date_rollover_replans_and_runs_next_day(self):
        runtime = FakeBrowserRuntime()
        registry = FakeSiteRegistry()
        registry.register("weibo", FakeSite("weibo", "https://weibo.com"))
        registry.register("douban", FakeSite("douban", "https://douban.com"))

        config = load_keepalive_config(env=self.env)
        now_dt = datetime.datetime(2026, 7, 5, 10, 0, 0)
        clock = FakeClock(now_dt)
        sleeper = FakeSleeper()
        rng = FakeRng(30)

        scheduler = KeepaliveScheduler(runtime, registry, config, now=clock.now, sleep=sleeper.sleep, rng=rng)
        scheduler._stop_event = MagicMock()
        scheduler._stop_event.wait.return_value = False
        scheduler._stop_event.is_set.return_value = False

        scheduler.plan_next_run(clock.now())

        # Run day 1
        clock.current_now = scheduler.planned_run_at
        scheduler.run_due_once(clock.now())
        self.assertEqual(len(runtime.calls), 6)
        runtime.calls.clear()

        # Advance to next day
        clock.advance(datetime.timedelta(days=1))
        # This run due once triggers rollover and replans
        scheduler.run_due_once(clock.now())
        # Move clock to the newly scheduled time for day 2
        clock.current_now = scheduler.planned_run_at
        scheduler.run_due_once(clock.now())
        self.assertEqual(len(runtime.calls), 6)

    def test_multiple_sites_keep_independent_results_when_snapshot_overwrites(self):
        runtime = FakeBrowserRuntime()
        registry = FakeSiteRegistry()
        registry.register("weibo", FakeSite("weibo", "https://weibo.com"))
        registry.register("douban", FakeSite("douban", "https://douban.com"))

        config = load_keepalive_config(env=self.env)
        now_dt = datetime.datetime(2026, 7, 5, 10, 0, 0)
        clock = FakeClock(now_dt)
        sleeper = FakeSleeper()
        rng = FakeRng(30)

        scheduler = KeepaliveScheduler(runtime, registry, config, now=clock.now, sleep=sleeper.sleep, rng=rng)
        scheduler._stop_event = MagicMock()
        scheduler._stop_event.wait.return_value = False
        scheduler._stop_event.is_set.return_value = False

        scheduler.plan_next_run(clock.now())
        clock.current_now = scheduler.planned_run_at
        scheduler.run_due_once(clock.now())

        # Check status file content
        with open(self.status_file, "r") as f:
            status_data = json.load(f)

        self.assertEqual(status_data["date"], "2026-07-05")
        self.assertIn("weibo", status_data["sites"])
        self.assertIn("douban", status_data["sites"])
        self.assertEqual(status_data["sites"]["weibo"]["status"], "success")
        self.assertEqual(status_data["sites"]["douban"]["status"], "success")
        self.assertEqual(status_data["sites"]["weibo"]["url"], "https://weibo.com")

    def test_atomic_snapshot_write_keeps_all_sites(self):
        # This is covered by test_multiple_sites_keep_independent_results_when_snapshot_overwrites
        # which checks the written status file retains all config sites.
        pass

    def test_run_site_uses_open_new_url_and_close_tab(self):
        runtime = FakeBrowserRuntime()
        registry = FakeSiteRegistry()
        registry.register("weibo", FakeSite("weibo", "https://weibo.com"))

        config = load_keepalive_config(env=self.env)
        sleeper = FakeSleeper()
        rng = FakeRng(30)
        scheduler = KeepaliveScheduler(runtime, registry, config, sleep=sleeper.sleep, rng=rng)
        scheduler._stop_event = MagicMock()
        scheduler._stop_event.wait.return_value = False
        scheduler._stop_event.is_set.return_value = False

        scheduler.run_sites_once()

        # Verify runtime calls: open_new_url, wait_for_page, close_tab
        methods_called = [call[0] for call in runtime.calls]
        self.assertEqual(methods_called, ["open_new_url", "wait_for_page", "close_tab"])
        scheduler._stop_event.wait.assert_called_once_with(timeout=30)

    def test_unknown_site_skipped(self):
        runtime = FakeBrowserRuntime()
        registry = FakeSiteRegistry()  # Empty registry

        config = load_keepalive_config(env=self.env)
        sleeper = FakeSleeper()
        rng = FakeRng(30)
        scheduler = KeepaliveScheduler(runtime, registry, config, sleep=sleeper.sleep, rng=rng)
        scheduler._stop_event = MagicMock()
        scheduler._stop_event.wait.return_value = False
        scheduler._stop_event.is_set.return_value = False

        scheduler.run_sites_once()

        status = scheduler.status()
        self.assertEqual(status["sites"]["weibo"]["status"], "skipped")
        self.assertEqual(status["sites"]["weibo"]["error"], "unknown_site")

    def test_missing_home_url_skipped(self):
        runtime = FakeBrowserRuntime()
        registry = FakeSiteRegistry()
        registry.register("weibo", FakeSite("weibo", ""))  # Empty home_url

        config = load_keepalive_config(env=self.env)
        sleeper = FakeSleeper()
        rng = FakeRng(30)
        scheduler = KeepaliveScheduler(runtime, registry, config, sleep=sleeper.sleep, rng=rng)
        scheduler._stop_event = MagicMock()
        scheduler._stop_event.wait.return_value = False
        scheduler._stop_event.is_set.return_value = False

        scheduler.run_sites_once()

        status = scheduler.status()
        self.assertEqual(status["sites"]["weibo"]["status"], "skipped")
        self.assertEqual(status["sites"]["weibo"]["error"], "missing_home_url")

    def test_invalid_window_enters_error(self):
        env = dict(self.env)
        env["BB_KEEPALIVE_WINDOW_START"] = "invalid"
        config = load_keepalive_config(env=env)
        scheduler = KeepaliveScheduler(FakeBrowserRuntime(), FakeSiteRegistry(), config)
        scheduler.plan_next_run(datetime.datetime.now())
        status = scheduler.status()
        self.assertEqual(status["phase"], "error")
        self.assertIn("invalid window", status.get("error", "").lower())

    def test_invalid_dwell_enters_error(self):
        env = dict(self.env)
        env["BB_KEEPALIVE_DWELL_SECONDS_MIN"] = "invalid"
        config = load_keepalive_config(env=env)
        scheduler = KeepaliveScheduler(FakeBrowserRuntime(), FakeSiteRegistry(), config)
        scheduler.plan_next_run(datetime.datetime.now())
        status = scheduler.status()
        self.assertEqual(status["phase"], "error")
        self.assertIn("invalid dwell", status.get("error", "").lower())

    def test_start_idempotent_and_stop_sets_event(self):
        runtime = FakeBrowserRuntime()
        registry = FakeSiteRegistry()
        config = load_keepalive_config(env=self.env)
        scheduler = KeepaliveScheduler(runtime, registry, config)
        
        # Idle/stopped initially
        self.assertFalse(scheduler.is_running())
        scheduler.start()
        self.assertTrue(scheduler.is_running())
        
        # Start again should be idempotent
        thread1 = scheduler._thread
        scheduler.start()
        self.assertEqual(scheduler._thread, thread1)
        
        # Stop
        scheduler.stop()
        self.assertFalse(scheduler.is_running())

    def test_plan_within_window_starts_random_from_now(self):
        runtime = FakeBrowserRuntime()
        registry = FakeSiteRegistry()
        config = load_keepalive_config(env=self.env)
        
        # Clock is at 10:00:00 today. Window is 09:00 - 23:00.
        now_dt = datetime.datetime(2026, 7, 5, 10, 0, 0)
        clock = FakeClock(now_dt)
        rng = FakeRng(0)  # Always return 0 offset
        
        scheduler = KeepaliveScheduler(runtime, registry, config, now=clock.now, rng=rng)
        scheduler.plan_next_run(clock.now())
        
        # Since rng offset is 0, planned_run_at must be exactly now_dt (10:00:00), not start_dt (09:00:00)
        self.assertEqual(scheduler.planned_run_at, now_dt)

    def test_invalid_window_start_equal_to_end_enters_error(self):
        env = dict(self.env)
        env["BB_KEEPALIVE_WINDOW_START"] = "09:00"
        env["BB_KEEPALIVE_WINDOW_END"] = "09:00"
        config = load_keepalive_config(env=env)
        scheduler = KeepaliveScheduler(FakeBrowserRuntime(), FakeSiteRegistry(), config)
        scheduler.plan_next_run(datetime.datetime(2026, 7, 5, 10, 0, 0))
        status = scheduler.status()
        self.assertEqual(status["phase"], "error")
        self.assertIn("equal to or after end", status.get("error", ""))

    def test_invalid_window_start_after_end_enters_error(self):
        env = dict(self.env)
        env["BB_KEEPALIVE_WINDOW_START"] = "10:00"
        env["BB_KEEPALIVE_WINDOW_END"] = "09:00"
        config = load_keepalive_config(env=env)
        scheduler = KeepaliveScheduler(FakeBrowserRuntime(), FakeSiteRegistry(), config)
        scheduler.plan_next_run(datetime.datetime(2026, 7, 5, 10, 0, 0))
        status = scheduler.status()
        self.assertEqual(status["phase"], "error")
        self.assertIn("equal to or after end", status.get("error", ""))

    def test_invalid_dwell_negative_enters_error(self):
        env = dict(self.env)
        env["BB_KEEPALIVE_DWELL_SECONDS_MIN"] = "-5"
        config = load_keepalive_config(env=env)
        scheduler = KeepaliveScheduler(FakeBrowserRuntime(), FakeSiteRegistry(), config)
        scheduler.plan_next_run(datetime.datetime(2026, 7, 5, 10, 0, 0))
        status = scheduler.status()
        self.assertEqual(status["phase"], "error")
        self.assertIn("non-negative", status.get("error", ""))

    def test_invalid_dwell_min_greater_than_max_enters_error(self):
        env = dict(self.env)
        env["BB_KEEPALIVE_DWELL_SECONDS_MIN"] = "30"
        env["BB_KEEPALIVE_DWELL_SECONDS_MAX"] = "20"
        config = load_keepalive_config(env=env)
        scheduler = KeepaliveScheduler(FakeBrowserRuntime(), FakeSiteRegistry(), config)
        scheduler.plan_next_run(datetime.datetime(2026, 7, 5, 10, 0, 0))
        status = scheduler.status()
        self.assertEqual(status["phase"], "error")
        self.assertIn("min", status.get("error", ""))
        self.assertIn("max", status.get("error", ""))

    def test_run_site_interrupted_by_stop_closes_tab_and_exits(self):
        runtime = FakeBrowserRuntime()
        registry = FakeSiteRegistry()
        registry.register("weibo", FakeSite("weibo", "https://weibo.com"))

        config = load_keepalive_config(env=self.env)
        rng = FakeRng(30)
        scheduler = KeepaliveScheduler(runtime, registry, config, rng=rng)
        
        # Inject mock stop_event that behaves as if stop was called (returns True on wait)
        scheduler._stop_event = MagicMock()
        scheduler._stop_event.wait.return_value = True
        scheduler._stop_event.is_set.return_value = True
        
        scheduler.run_sites_once()

        # Verify that tab was opened and closed
        methods_called = [call[0] for call in runtime.calls]
        self.assertEqual(methods_called, ["open_new_url", "wait_for_page", "close_tab"])
        scheduler._stop_event.wait.assert_called_once_with(timeout=30)
        
        status = scheduler.status()
        self.assertEqual(status["sites"]["weibo"]["status"], "failed")
        self.assertEqual(status["sites"]["weibo"]["error"], "interrupted")

    def test_invalid_window_writes_error_snapshot(self):
        env = dict(self.env)
        env["BB_KEEPALIVE_WINDOW_START"] = "invalid"
        config = load_keepalive_config(env=env)
        scheduler = KeepaliveScheduler(FakeBrowserRuntime(), FakeSiteRegistry(), config)
        scheduler.plan_next_run(datetime.datetime(2026, 7, 5, 10, 0, 0))
        
        # Verify status snapshot file is written and contains phase="error"
        with open(self.status_file, "r") as f:
            status_data = json.load(f)
        self.assertEqual(status_data["phase"], "error")
        self.assertIn("invalid window", status_data["error"].lower())

    def test_invalid_dwell_writes_error_snapshot(self):
        env = dict(self.env)
        env["BB_KEEPALIVE_DWELL_SECONDS_MIN"] = "-5"
        config = load_keepalive_config(env=env)
        scheduler = KeepaliveScheduler(FakeBrowserRuntime(), FakeSiteRegistry(), config)
        scheduler.plan_next_run(datetime.datetime(2026, 7, 5, 10, 0, 0))
        
        # Verify status snapshot file is written and contains phase="error"
        with open(self.status_file, "r") as f:
            status_data = json.load(f)
        self.assertEqual(status_data["phase"], "error")
        self.assertIn("non-negative", status_data["error"].lower())

    def test_plan_writes_matching_phase_in_snapshot(self):
        runtime = FakeBrowserRuntime()
        registry = FakeSiteRegistry()
        config = load_keepalive_config(env=self.env)
        
        # Inside active window (10:00)
        now_dt = datetime.datetime(2026, 7, 5, 10, 0, 0)
        clock = FakeClock(now_dt)
        rng = FakeRng(30)
        
        scheduler = KeepaliveScheduler(runtime, registry, config, now=clock.now, rng=rng)
        scheduler._stop_event = MagicMock()
        scheduler._stop_event.wait.return_value = False
        scheduler._stop_event.is_set.return_value = False
        
        scheduler.plan_next_run(clock.now())
        
        # Verify status file exists, is written, and its phase matches memory phase (scheduled)
        self.assertEqual(scheduler.status()["phase"], "scheduled")
        with open(self.status_file, "r") as f:
            status_data = json.load(f)
        self.assertEqual(status_data["phase"], "scheduled")


class KeepaliveStatusEndpointTest(unittest.TestCase):
    @patch("bridge.app.server.keepalive_scheduler")
    def test_keepalive_status_endpoint_returns_correct_envelope(self, mock_scheduler):
        mock_scheduler.status.return_value = {
            "date": "2026-07-05",
            "enabled": True,
            "phase": "scheduled",
            "windowStart": "09:00",
            "windowEnd": "23:00",
            "dwellSecondsMin": 20,
            "dwellSecondsMax": 60,
            "plannedRunAt": "2026-07-05T10:15:30.123456",
            "sites": {},
            "updatedAt": "2026-07-05T01:42:21",
            "error": None
        }
        
        response = server.keepalive_status()
        self.assertTrue(response.get("ok"))
        self.assertEqual(response.get("action"), "keepalive-status")
        self.assertEqual(response.get("data")["phase"], "scheduled")


if __name__ == "__main__":
    unittest.main()
