from ..read_only_site import ReadOnlySite


class WikipediaSite(ReadOnlySite):
    site_id = "wikipedia"
    hosts = {"wikipedia.org"}
    home_url = "https://www.wikipedia.org/"
    search_url_template = "https://en.wikipedia.org/w/index.php?search={keyword}"
    search_ready_selector = "#content, main, a[href*='/wiki/']"
