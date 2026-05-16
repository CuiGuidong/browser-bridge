from ..read_only_site import ReadOnlySite


class TiebaSite(ReadOnlySite):
    site_id = "tieba"
    hosts = {"tieba.baidu.com"}
    home_url = "https://tieba.baidu.com/"
    search_url_template = "https://tieba.baidu.com/f/search/res?qw={keyword}&ie=utf-8&pn=1"
    search_ready_selector = "a[href*='/p/'], .threadcardclass"
