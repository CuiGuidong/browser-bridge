from ..read_only_site import ReadOnlySite


class JdSite(ReadOnlySite):
    site_id = "jd"
    hosts = {"jd.com", "360buy.com"}
    home_url = "https://www.jd.com/"
    search_url_template = "https://search.jd.com/Search?keyword={keyword}&enc=utf-8"
    search_ready_selector = "a[href*='item.jd.com'], main, #J_goodsList"
