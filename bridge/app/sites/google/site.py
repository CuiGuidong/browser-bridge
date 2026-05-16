from ..read_only_site import ReadOnlySite


class GoogleSite(ReadOnlySite):
    site_id = "google"
    hosts = {"google.com"}
    home_url = "https://www.google.com/"
    search_url_template = "https://www.google.com/search?q={keyword}"
    search_ready_selector = "a[href], #search"
