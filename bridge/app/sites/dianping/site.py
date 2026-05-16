from ..read_only_site import ReadOnlySite


class DianpingSite(ReadOnlySite):
    site_id = "dianping"
    hosts = {"dianping.com"}
    home_url = "https://www.dianping.com/"
    search_url_template = "https://www.dianping.com/search/keyword/1/0_{keyword}"
    search_ready_selector = "main, a[href*='/shop/'], a[href]"
