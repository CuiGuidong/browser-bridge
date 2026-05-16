from ..opencli_inspired import OpenCliInspiredReadOnlySite


class WeixinSite(OpenCliInspiredReadOnlySite):
    site_id = "weixin"
    hosts = {"mp.weixin.qq.com", "weixin.sogou.com"}
    home_url = "https://mp.weixin.qq.com/"
    search_url_template = "https://weixin.sogou.com/weixin?type=2&query={keyword}"
