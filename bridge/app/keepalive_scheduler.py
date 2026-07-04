import os
import json
import time
import random
import datetime
import logging
import threading
import tempfile
import platform

logger = logging.getLogger("browser-bridge.keepalive")


class KeepaliveConfig:
    def __init__(self, enabled, sites, window_start, window_end, dwell_seconds_min, dwell_seconds_max, status_file):
        self.enabled = enabled
        self.sites = sites
        self.window_start = window_start
        self.window_end = window_end
        self.dwell_seconds_min = dwell_seconds_min
        self.dwell_seconds_max = dwell_seconds_max
        self.status_file = status_file


def load_keepalive_config(env=None, platform_system=None, home=None):
    if env is None:
        env = os.environ
    if platform_system is None:
        platform_system = platform.system()
    if home is None:
        home = os.path.expanduser("~")

    enabled = env.get("BB_KEEPALIVE_ENABLED", "false").lower() == "true"
    
    sites_raw = env.get("BB_KEEPALIVE_SITES", "")
    sites = [s.strip() for s in sites_raw.split(",") if s.strip()]
    
    window_start = env.get("BB_KEEPALIVE_WINDOW_START", "09:00")
    window_end = env.get("BB_KEEPALIVE_WINDOW_END", "23:00")
    
    def get_int(key, default):
        val = env.get(key)
        if val is None or val == "":
            return default
        try:
            return int(val)
        except ValueError:
            return "invalid"

    dwell_seconds_min = get_int("BB_KEEPALIVE_DWELL_SECONDS_MIN", 20)
    dwell_seconds_max = get_int("BB_KEEPALIVE_DWELL_SECONDS_MAX", 60)
    
    status_file = env.get("BB_KEEPALIVE_STATUS_FILE")
    if not status_file:
        if platform_system == "Windows":
            local_app_data = env.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
            status_file = os.path.join(local_app_data, "BrowserBridge", "browser-bridge-keepalive-status.json")
        elif platform_system == "Darwin":
            status_file = os.path.join(home, "Library", "Application Support", "BrowserBridge", "browser-bridge-keepalive-status.json")
        else:
            # Linux and others
            xdg_state_home = env.get("XDG_STATE_HOME")
            if not xdg_state_home:
                xdg_state_home = os.path.join(home, ".local", "state")
            status_file = os.path.join(xdg_state_home, "browser-bridge", "browser-bridge-keepalive-status.json")

    if status_file and platform_system == "Windows":
        status_file = status_file.replace("/", "\\")

    return KeepaliveConfig(
        enabled=enabled,
        sites=sites,
        window_start=window_start,
        window_end=window_end,
        dwell_seconds_min=dwell_seconds_min,
        dwell_seconds_max=dwell_seconds_max,
        status_file=status_file
    )


class KeepaliveScheduler:
    def __init__(self, browser_runtime, site_registry, config, now=None, sleep=None, rng=None):
        self.browser_runtime = browser_runtime
        self.site_registry = site_registry
        self.config = config
        
        self.now_fn = now if now else datetime.datetime.now
        self.sleep_fn = sleep if sleep else time.sleep
        
        if rng:
            self.rng = rng
        else:
            self.rng = random

        self._stop_event = threading.Event()
        self._thread = None
        
        # Initialize internal status dict
        self._status = {
            "enabled": config.enabled,
            "phase": "disabled" if not config.enabled else "waiting_window",
            "sites": {},
            "error": None
        }
        
        # Pre-populate sites info
        for site in config.sites:
            site_module = site_registry.get(site)
            home_url = getattr(site_module, "home_url", None) if site_module else None
            self._status["sites"][site] = {
                "url": home_url,
                "status": "pending",
                "lastAttemptAt": None,
                "lastDwellSeconds": None,
                "lastResult": None,
                "error": None
            }

        self.planned_run_at = None
        self.last_run_date = None
        
        # Initial plan if enabled
        if config.enabled:
            self.plan_next_run(self.now_fn())

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if not self.config.enabled:
            logger.info("Keepalive is disabled. Thread not started.")
            return
        if self.is_running():
            logger.info("Keepalive scheduler already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="KeepaliveSchedulerThread", daemon=True)
        self._thread.start()
        logger.info("Keepalive scheduler thread started.")

    def stop(self, timeout_seconds=5):
        if not self.is_running():
            return True
        self._stop_event.set()
        self._thread.join(timeout=timeout_seconds)
        stopped = not self.is_running()
        if stopped:
            self._thread = None
            logger.info("Keepalive scheduler thread stopped.")
        else:
            logger.warning("Failed to stop Keepalive scheduler thread within timeout.")
        return stopped

    def status(self):
        # Build live status mapping conforming to spec
        return {
            "date": str(self.now_fn().date()),
            "enabled": self.config.enabled,
            "phase": self._status.get("phase"),
            "windowStart": self.config.window_start,
            "windowEnd": self.config.window_end,
            "dwellSecondsMin": self.config.dwell_seconds_min,
            "dwellSecondsMax": self.config.dwell_seconds_max,
            "plannedRunAt": self.planned_run_at.isoformat() if self.planned_run_at else None,
            "sites": self._status.get("sites"),
            "updatedAt": self.now_fn().isoformat(),
            "error": self._status.get("error")
        }

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                now = self.now_fn()
                self.run_due_once(now)
            except Exception as e:
                logger.error(f"Error in keepalive loop: {e}", exc_info=True)
            # Sleep in small steps to remain responsive to stop event
            for _ in range(5):
                if self._stop_event.is_set():
                    break
                self.sleep_fn(1)

    def plan_next_run(self, now):
        if not self.config.enabled:
            self._status["phase"] = "disabled"
            return

        # Check for date rollover
        if self.last_run_date is not None and now.date() > self.last_run_date:
            # Clean up/rollover date
            logger.info(f"Date rollover detected: {self.last_run_date} -> {now.date()}")
            self.last_run_date = None
            # Reset site run states
            for site in self.config.sites:
                site_module = self.site_registry.get(site)
                home_url = getattr(site_module, "home_url", None) if site_module else None
                self._status["sites"][site] = {
                    "url": home_url,
                    "status": "pending",
                    "lastAttemptAt": None,
                    "lastDwellSeconds": None,
                    "lastResult": None,
                    "error": None
                }
            self._write_snapshot()

        # Parse window times
        try:
            sh, sm = map(int, self.config.window_start.split(":"))
            eh, em = map(int, self.config.window_end.split(":"))
            start_time_of_day = datetime.time(sh, sm)
            end_time_of_day = datetime.time(eh, em)
        except Exception as e:
            self._status["phase"] = "error"
            self._status["error"] = f"Invalid window config '{self.config.window_start}-{self.config.window_end}': {e}"
            self.planned_run_at = None
            self._write_snapshot()
            return

        # Validate dwell times
        if not isinstance(self.config.dwell_seconds_min, int) or not isinstance(self.config.dwell_seconds_max, int):
            self._status["phase"] = "error"
            self._status["error"] = "Invalid dwell configuration: values must be integers"
            self.planned_run_at = None
            self._write_snapshot()
            return

        if self.config.dwell_seconds_min < 0 or self.config.dwell_seconds_max < 0:
            self._status["phase"] = "error"
            self._status["error"] = "Invalid dwell configuration: values must be non-negative"
            self.planned_run_at = None
            self._write_snapshot()
            return

        if self.config.dwell_seconds_min > self.config.dwell_seconds_max:
            self._status["phase"] = "error"
            self._status["error"] = f"Invalid dwell configuration: min ({self.config.dwell_seconds_min}) > max ({self.config.dwell_seconds_max})"
            self.planned_run_at = None
            self._write_snapshot()
            return

        # Clear error if parsing succeeded now
        self._status["error"] = None

        # Determine target date to schedule
        target_date = now.date()
        if self.last_run_date == now.date():
            # Already completed today, schedule for tomorrow
            target_date = now.date() + datetime.timedelta(days=1)
        else:
            # Check if now is past today's window end
            today_end = datetime.datetime.combine(now.date(), end_time_of_day)
            if now >= today_end:
                target_date = now.date() + datetime.timedelta(days=1)

        # Calculate scheduling time
        if self.planned_run_at is not None and self.planned_run_at.date() == target_date:
            # Already planned for the correct target date, don't change
            pass
        else:
            start_dt = datetime.datetime.combine(target_date, start_time_of_day)
            end_dt = datetime.datetime.combine(target_date, end_time_of_day)
            
            # Check window bounds validity
            if int((end_dt - start_dt).total_seconds()) <= 0:
                self._status["phase"] = "error"
                self._status["error"] = f"Invalid window config: start ({self.config.window_start}) equal to or after end ({self.config.window_end})"
                self.planned_run_at = None
                self._write_snapshot()
                return

            # If scheduling for today and we started inside/after window start
            if target_date == now.date() and now > start_dt:
                effective_start_dt = now
            else:
                effective_start_dt = start_dt

            diff_seconds = int((end_dt - effective_start_dt).total_seconds())
            random_offset = self.rng.randint(0, diff_seconds) if diff_seconds > 0 else 0
            self.planned_run_at = effective_start_dt + datetime.timedelta(seconds=random_offset)
            logger.info(f"Planned next keepalive run for {self.planned_run_at}")

        # Update current phase description
        now_start_dt = datetime.datetime.combine(now.date(), start_time_of_day)
        now_end_dt = datetime.datetime.combine(now.date(), end_time_of_day)
        
        if self.last_run_date == now.date():
            self._status["phase"] = "completed"
        elif now_start_dt <= now <= now_end_dt:
            self._status["phase"] = "scheduled"
        else:
            self._status["phase"] = "waiting_window"

        self._write_snapshot()

    def run_due_once(self, now=None):
        if now is None:
            now = self.now_fn()
        self.plan_next_run(now)
        if self._status["phase"] in ("error", "disabled"):
            return
        if self.planned_run_at is not None and now >= self.planned_run_at:
            if self.last_run_date != now.date():
                self.run_sites_once()

    def run_sites_once(self):
        self._status["phase"] = "running"
        self._write_snapshot()
        
        logger.info(f"Starting keepalive run for sites: {self.config.sites}")
        
        for site in self.config.sites:
            site_info = self._status["sites"][site]
            site_info["lastAttemptAt"] = self.now_fn().isoformat()
            site_info["status"] = "running"
            site_info["error"] = None
            self._write_snapshot()
            
            site_module = self.site_registry.get(site)
            if not site_module:
                site_info["status"] = "skipped"
                site_info["error"] = "unknown_site"
                logger.warning(f"Skipping keepalive for site '{site}': Site not registered")
                self._write_snapshot()
                continue
                
            home_url = getattr(site_module, "home_url", None)
            site_info["url"] = home_url
            if not home_url:
                site_info["status"] = "skipped"
                site_info["error"] = "missing_home_url"
                logger.warning(f"Skipping keepalive for site '{site}': home_url not defined")
                self._write_snapshot()
                continue
                
            dwell = self.rng.randint(self.config.dwell_seconds_min, self.config.dwell_seconds_max)
            
            tab_id = None
            try:
                tab = self.browser_runtime.open_new_url(home_url)
                if not tab:
                    site_info["status"] = "failed"
                    site_info["error"] = "failed_to_open_page"
                    logger.error(f"Failed to open page '{home_url}' for site '{site}' keepalive")
                    self._write_snapshot()
                    continue
                
                tab_id = tab.get("nativeTabId")
                wait_res = self.browser_runtime.wait_for_page(tab_id, timeout_seconds=15)
                if not wait_res or not wait_res.get("stable"):
                    site_info["status"] = "failed"
                    site_info["error"] = "page_not_stable"
                    logger.error(f"Page was not stable '{home_url}' for site '{site}' keepalive")
                    self._write_snapshot()
                    continue
                
                # Perform stop-aware dwell sleep
                stopped = self._stop_event.wait(timeout=dwell)
                
                if stopped:
                    logger.info("Keepalive run interrupted during dwell due to scheduler stop.")
                    site_info["status"] = "failed"
                    site_info["error"] = "interrupted"
                    self._write_snapshot()
                    return

                close_res = self.browser_runtime.close_tab(tab_id)
                tab_id = None  # Cleared as closed successfully or attempted

                if not close_res or not close_res.get("closed"):
                    site_info["status"] = "failed"
                    site_info["error"] = "failed_to_close_tab"
                    logger.error(f"Failed to close tab for site '{site}' keepalive")
                    self._write_snapshot()
                    continue
                
                site_info["status"] = "success"
                site_info["lastDwellSeconds"] = dwell
                site_info["lastResult"] = "OK"
                site_info["error"] = None
                
            except Exception as e:
                logger.error(f"Exception during site '{site}' keepalive: {e}", exc_info=True)
                site_info["status"] = "failed"
                site_info["error"] = str(e)
            finally:
                if tab_id:
                    try:
                        self.browser_runtime.close_tab(tab_id)
                    except Exception as ce:
                        logger.error(f"Failed in fallback tab close for site '{site}': {ce}")
                
            self._write_snapshot()

        self.last_run_date = self.now_fn().date()
        self._status["phase"] = "completed"
        self._write_snapshot()
        logger.info(f"Keepalive run completed for date {self.last_run_date}")

    def _write_snapshot(self):
        if not self.config.status_file:
            return
        
        data = self.status()
        
        try:
            dir_name = os.path.dirname(self.config.status_file)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            
            temp_fd, temp_path = tempfile.mkstemp(dir=dir_name)
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                os.replace(temp_path, self.config.status_file)
            except Exception:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise
        except Exception as e:
            logger.error(f"Failed to write keepalive status snapshot to '{self.config.status_file}': {e}")
