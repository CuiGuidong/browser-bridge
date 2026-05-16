from ..read_only_site import ReadOnlySite


class Site36krSite(ReadOnlySite):
    site_id = "36kr"
    hosts = {"36kr.com"}
    home_url = "https://www.36kr.com/"
    search_url_template = "https://www.36kr.com/search/articles/{keyword}"
    search_ready_selector = "a[href*='/p/'], article"
