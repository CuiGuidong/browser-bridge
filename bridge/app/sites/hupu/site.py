from ..read_only_site import ReadOnlySite


class HupuSite(ReadOnlySite):
    site_id = "hupu"
    hosts = {"hupu.com"}
    home_url = "https://bbs.hupu.com/"
    search_url_template = "https://bbs.hupu.com/search?q={keyword}"
    search_ready_selector = "a[href*='/'], main, article"
