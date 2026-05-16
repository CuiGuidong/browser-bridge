from ..opencli_inspired import OpenCliInspiredReadOnlySite


class HackerNewsSite(OpenCliInspiredReadOnlySite):
    site_id = "hackernews"
    hosts = {"news.ycombinator.com", "hn.algolia.com"}
    home_url = "https://news.ycombinator.com/"
    search_url_template = "https://hn.algolia.com/?q={keyword}"
    search_ready_selector = ".Story"
