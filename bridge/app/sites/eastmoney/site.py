from ..read_only_site import ReadOnlySite


class EastmoneySite(ReadOnlySite):
    site_id = "eastmoney"
    hosts = {"eastmoney.com", "eastmoney.cn"}
    home_url = "https://www.eastmoney.com/"
    search_url_template = "https://so.eastmoney.com/web/s?keyword={keyword}"
