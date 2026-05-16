from ..read_only_site import ReadOnlySite


class Ali1688Site(ReadOnlySite):
    site_id = "1688"
    hosts = {"1688.com"}
    home_url = "https://www.1688.com/"
    search_url_template = "https://s.1688.com/selloffer/offer_search.htm?charset=utf8&keywords={keyword}"
    search_ready_selector = "a[href*='/offer/'], a[href*='offer_search']"
