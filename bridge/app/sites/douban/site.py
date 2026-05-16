from ..read_only_site import ReadOnlySite


class DoubanSite(ReadOnlySite):
    site_id = "douban"
    hosts = {"douban.com"}
    home_url = "https://www.douban.com/"
    search_url_template = "https://www.douban.com/search?q={keyword}"
