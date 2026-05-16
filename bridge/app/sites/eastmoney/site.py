from ..opencli_inspired import OpenCliInspiredReadOnlySite


class EastmoneySite(OpenCliInspiredReadOnlySite):
    site_id = "eastmoney"
    hosts = {"eastmoney.com", "eastmoney.cn"}
    home_url = "https://www.eastmoney.com/"
    search_url_template = "https://so.eastmoney.com/web/s?keyword={keyword}"
