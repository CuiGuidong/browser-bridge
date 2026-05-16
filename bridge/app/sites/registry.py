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
