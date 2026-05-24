class SiteRegistry:
    def __init__(self):
        self._sites = {}

    def register(self, site_id, site_module):
        self._sites[site_id] = site_module

    def get(self, site_id):
        return self._sites.get(site_id)

    def list_sites(self):
        return sorted(self._sites.keys())

    def capabilities(self):
        return {
            site_id: site_module.capabilities()
            for site_id, site_module in sorted(self._sites.items())
        }

    def get_allowed_hosts(self) -> list[str]:
        hosts = set()
        for site_module in self._sites.values():
            if hasattr(site_module, "hosts") and site_module.hosts:
                for host in site_module.hosts:
                    hosts.add(host)
        return sorted(list(hosts))
