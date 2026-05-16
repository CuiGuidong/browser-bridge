from ..read_only_site import ReadOnlySite


class XueqiuSite(ReadOnlySite):
    site_id = "xueqiu"
    hosts = {"xueqiu.com"}
    home_url = "https://xueqiu.com/"
    search_url_template = "https://xueqiu.com/k?q={keyword}"
