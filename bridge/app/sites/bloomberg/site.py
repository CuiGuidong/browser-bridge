from ..read_only_site import ReadOnlySite


class BloombergSite(ReadOnlySite):
    site_id = "bloomberg"
    hosts = {"bloomberg.com"}
    home_url = "https://www.bloomberg.com/"
    search_url_template = "https://www.bloomberg.com/search?query={keyword}"
    search_ready_selector = "main, article, a[href*='/news/']"
