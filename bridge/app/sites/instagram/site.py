from ..opencli_inspired import OpenCliInspiredReadOnlySite


class InstagramSite(OpenCliInspiredReadOnlySite):
    site_id = "instagram"
    hosts = {"instagram.com"}
    home_url = "https://www.instagram.com/"
    search_url_template = "https://www.instagram.com/explore/search/keyword/?q={keyword}"
