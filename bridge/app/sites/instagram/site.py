from ..read_only_site import ReadOnlySite


class InstagramSite(ReadOnlySite):
    site_id = "instagram"
    hosts = {"instagram.com"}
    home_url = "https://www.instagram.com/"
    search_url_template = "https://www.instagram.com/explore/search/keyword/?q={keyword}"
