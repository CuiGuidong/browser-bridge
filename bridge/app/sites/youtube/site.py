from ..read_only_site import ReadOnlySite


class YoutubeSite(ReadOnlySite):
    site_id = "youtube"
    hosts = {"youtube.com", "youtu.be"}
    home_url = "https://www.youtube.com/"
    search_url_template = "https://www.youtube.com/results?search_query={keyword}"
