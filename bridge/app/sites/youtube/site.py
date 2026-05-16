from ..opencli_inspired import OpenCliInspiredReadOnlySite


class YoutubeSite(OpenCliInspiredReadOnlySite):
    site_id = "youtube"
    hosts = {"youtube.com", "youtu.be"}
    home_url = "https://www.youtube.com/"
    search_url_template = "https://www.youtube.com/results?search_query={keyword}"
