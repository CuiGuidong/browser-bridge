from ..read_only_site import ReadOnlySite


class AibaseSite(ReadOnlySite):
    site_id = "aibase"
    hosts = {"aibase.com"}
    home_url = "https://www.aibase.com/zh/daily"
    search_url_template = "https://www.aibase.com/zh/search?q={keyword}"
    search_ready_selector = "main, article, a[href]"
