class LoginService:
    def __init__(self, workflow_service, notification_service):
        self.workflow_service = workflow_service
        self.notification_service = notification_service

    def status(self, site, target_id=None, notify=False, timeout_seconds=20):
        result = self.workflow_service.run(
            site=site,
            workflow="account_status",
            params={},
            target_id=target_id,
            timeout_seconds=timeout_seconds,
        )
        notification = None
        content = (result or {}).get("content") or {}
        if notify and result and result.get("ok") and content.get("needsHumanLogin"):
            notification = self.notification_service.send_login_alert(result)
        return {
            "status": result,
            "notification": notification,
        }

    def status_many(self, sites, notify=False, timeout_seconds=20):
        results = []
        for site in sites:
            results.append({
                "site": site,
                **self.status(
                    site=site,
                    notify=notify,
                    timeout_seconds=timeout_seconds,
                ),
            })
        return {
            "results": results,
        }
