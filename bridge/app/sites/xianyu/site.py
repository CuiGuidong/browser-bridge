from ..read_only_site import ReadOnlySite


class XianyuSite(ReadOnlySite):
    site_id = "xianyu"
    hosts = {"goofish.com", "xianyu.taobao.com"}
    home_url = "https://www.goofish.com/"
    search_url_template = "https://www.goofish.com/search?q={keyword}"
    search_ready_selector = "a[href*='/item'], main, a[href]"
