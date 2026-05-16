from ..read_only_site import ReadOnlySite


class GrokSite(ReadOnlySite):
    site_id = "grok"
    hosts = {"grok.com", "x.ai"}
    home_url = "https://grok.com/"
    search_url_template = "https://grok.com/"
    search_ready_selector = "main, textarea, [contenteditable='true']"
