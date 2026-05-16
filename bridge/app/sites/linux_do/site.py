from ..read_only_site import ReadOnlySite


class LinuxDoSite(ReadOnlySite):
    site_id = "linux-do"
    hosts = {"linux.do"}
    home_url = "https://linux.do/"
    search_url_template = "https://linux.do/search?q={keyword}"
    search_ready_selector = "a[href*='/t/'], main, .topic-list"
