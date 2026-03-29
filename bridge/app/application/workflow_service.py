class WorkflowService:
    def __init__(self, browser_runtime, extension_runtime, site_registry=None):
        self.browser_runtime = browser_runtime
        self.extension_runtime = extension_runtime
        self.site_registry = site_registry
        self.read_service = None
        self.action_service = None

    def bind_read_service(self, read_service):
        self.read_service = read_service
        return self

    def bind_action_service(self, action_service):
        self.action_service = action_service
        return self

    def status(self):
        return {
            "ready": self.read_service is not None,
            "message": "workflow layer ready" if self.read_service else "workflow layer not implemented yet",
        }

    def run(self, site, workflow, params=None, target_id=None, timeout_seconds=20):
        site_module = self.site_registry.get(site) if (self.site_registry and site) else None
        if site_module is None:
            return {
                "ok": False,
                "site": site,
                "workflow": workflow,
                "error": "site not supported",
            }
        if self.read_service is None:
            return {
                "ok": False,
                "site": site,
                "workflow": workflow,
                "error": "read service not bound",
            }
        if not hasattr(site_module, "run_workflow"):
            return {
                "ok": False,
                "site": site,
                "workflow": workflow,
                "error": "workflow not supported",
            }
        return site_module.run_workflow(
            workflow=workflow,
            params=params or {},
            target_id=target_id,
            timeout_seconds=timeout_seconds,
            browser_runtime=self.browser_runtime,
            extension_runtime=self.extension_runtime,
            read_service=self.read_service,
            action_service=self.action_service,
        )
