from ..read_only_site import ReadOnlySite


class TaobaoSite(ReadOnlySite):
    site_id = "taobao"
    hosts = {"taobao.com", "tmall.com"}
    home_url = "https://www.taobao.com/"
    search_url_template = "https://s.taobao.com/search?q={keyword}"
    search_ready_selector = "a[href*='item'], main, #mainsrp-itemlist"
