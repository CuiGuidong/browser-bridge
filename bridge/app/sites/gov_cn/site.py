from ..read_only_site import ReadOnlySite


class GovCnSite(ReadOnlySite):
    site_id = "gov.cn"
    hosts = {"gov.cn"}
    home_url = "https://www.gov.cn/"
    search_url_template = "https://sousuo.www.gov.cn/sousuo/search.shtml?searchWord={keyword}"
    search_ready_selector = "a[href], .result, .list"
