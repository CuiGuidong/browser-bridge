from ..opencli_inspired import OpenCliInspiredReadOnlySite


class XueqiuSite(OpenCliInspiredReadOnlySite):
    site_id = "xueqiu"
    hosts = {"xueqiu.com"}
    home_url = "https://xueqiu.com/"
    search_url_template = "https://xueqiu.com/k?q={keyword}"
