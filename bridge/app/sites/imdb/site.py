from ..read_only_site import ReadOnlySite


class ImdbSite(ReadOnlySite):
    site_id = "imdb"
    hosts = {"imdb.com"}
    home_url = "https://www.imdb.com/"
    search_url_template = "https://www.imdb.com/find/?q={keyword}"
    search_ready_selector = "a[href*='/title/'], a[href*='/name/'], main"
