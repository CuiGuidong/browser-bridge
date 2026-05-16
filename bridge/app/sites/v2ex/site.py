from ..read_only_site import ReadOnlySite


class V2exSite(ReadOnlySite):
    site_id = "v2ex"
    hosts = {"v2ex.com"}
    home_url = "https://www.v2ex.com/"
    search_url_template = "https://www.v2ex.com/search?q={keyword}"
    search_ready_selector = "a[href*='/t/'], #Wrapper"
