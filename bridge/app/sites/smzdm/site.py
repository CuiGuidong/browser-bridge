from ..read_only_site import ReadOnlySite


class SmzdmSite(ReadOnlySite):
    site_id = "smzdm"
    hosts = {"smzdm.com"}
    home_url = "https://www.smzdm.com/"
    search_url_template = "https://search.smzdm.com/?c=home&s={keyword}&v=b"
    search_ready_selector = "a[href], article, main"
