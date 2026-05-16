(function registerMediaAdapters() {
  window.BrowserBridgeAdapters = window.BrowserBridgeAdapters || [];

  const SITE_CONFIGS = {
    zhihu: {
      hosts: ['zhihu.com'],
      mediaType: 'article',
      read: ['read_post', 'read_profile_metrics', 'search', 'read_hot', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search')) return 'search';
        if (path.startsWith('/hot')) return 'hot';
        if (path.startsWith('/people/') || path.startsWith('/org/')) return 'profile';
        if (path.startsWith('/question/') || path.startsWith('/p/') || path.includes('/answer/')) return 'post';
        return 'unknown';
      },
    },
    bilibili: {
      hosts: ['bilibili.com', 'b23.tv'],
      mediaType: 'video',
      read: ['read_post', 'read_profile_metrics', 'search', 'read_hot', 'account_status'],
      pathType(path, host) {
        if (host === 'search.bilibili.com' || path.startsWith('/all')) return 'search';
        if (path.startsWith('/v/popular') || path.startsWith('/ranking')) return 'hot';
        if (host === 'space.bilibili.com') return 'profile';
        if (path.startsWith('/video/') || path.startsWith('/opus/')) return 'post';
        return 'unknown';
      },
    },
    douyin: {
      hosts: ['douyin.com', 'iesdouyin.com'],
      mediaType: 'video',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search/')) return 'search';
        if (path.startsWith('/user/')) return 'profile';
        if (path.startsWith('/video/') || path.startsWith('/note/')) return 'post';
        return 'unknown';
      },
    },
    reddit: {
      hosts: ['reddit.com'],
      mediaType: 'discussion',
      read: ['read_post', 'read_profile_metrics', 'search', 'read_hot', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search')) return 'search';
        if (path === '/hot/' || path === '/hot' || path === '/' || path.startsWith('/r/popular')) return 'hot';
        if (path.startsWith('/user/')) return 'profile';
        if (path.includes('/comments/')) return 'post';
        if (path.startsWith('/r/')) return 'profile';
        return 'unknown';
      },
    },
    youtube: {
      hosts: ['youtube.com', 'youtu.be'],
      mediaType: 'video',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path, host) {
        if (path.startsWith('/results')) return 'search';
        if (path.startsWith('/@') || path.startsWith('/channel/') || path.startsWith('/c/')) return 'profile';
        if (path.startsWith('/watch') || path.startsWith('/shorts/') || host === 'youtu.be') return 'post';
        return 'unknown';
      },
    },
    weixin: {
      hosts: ['mp.weixin.qq.com', 'weixin.sogou.com'],
      mediaType: 'article',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path, host) {
        if (host === 'weixin.sogou.com') return 'search';
        if (path.startsWith('/s') || path.startsWith('/s/')) return 'post';
        return 'unknown';
      },
    },
    douban: {
      hosts: ['douban.com'],
      mediaType: 'article',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search')) return 'search';
        if (path.startsWith('/people/') || path.startsWith('/group/')) return 'profile';
        if (path.startsWith('/subject/') || path.startsWith('/note/') || path.includes('/review/')) return 'post';
        return 'unknown';
      },
    },
    hackernews: {
      hosts: ['news.ycombinator.com', 'hn.algolia.com'],
      mediaType: 'discussion',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path, host) {
        if (host === 'hn.algolia.com') return 'search';
        if (path === '/user') return 'profile';
        if (path === '/item') return 'post';
        if (path === '/' || path === '/news') return 'search';
        return 'unknown';
      },
    },
    instagram: {
      hosts: ['instagram.com'],
      mediaType: 'image',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/explore/search')) return 'search';
        if (path.startsWith('/p/') || path.startsWith('/reel/') || path.startsWith('/tv/')) return 'post';
        if (/^\/[^/]+\/?$/.test(path) && !path.startsWith('/accounts')) return 'profile';
        return 'unknown';
      },
    },
    xueqiu: {
      hosts: ['xueqiu.com'],
      mediaType: 'finance',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/k') || path.startsWith('/S/')) return 'search';
        if (path.startsWith('/u/')) return 'profile';
        if (path.startsWith('/statuses/') || path.startsWith('/discussion/')) return 'post';
        return 'unknown';
      },
    },
    eastmoney: {
      hosts: ['eastmoney.com', 'eastmoney.cn'],
      mediaType: 'finance',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path, host) {
        if (host.startsWith('so.')) return 'search';
        if (path.includes('/quote') || path.includes('/stock')) return 'post';
        return path === '/' ? 'search' : 'unknown';
      },
    },
    1688: {
      hosts: ['1688.com'],
      mediaType: 'product',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path, host) {
        if (host === 's.1688.com' || path.includes('offer_search')) return 'search';
        if (host.startsWith('detail.') || path.includes('/offer/')) return 'post';
        if (host.endsWith('.1688.com') && host !== 'www.1688.com') return 'profile';
        return path === '/' ? 'search' : 'unknown';
      },
    },
    '36kr': {
      hosts: ['36kr.com'],
      mediaType: 'article',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search')) return 'search';
        if (path.startsWith('/p/')) return 'post';
        if (path.startsWith('/user/') || path.startsWith('/author/')) return 'profile';
        return path.startsWith('/hot-list') || path === '/' ? 'search' : 'unknown';
      },
    },
    tieba: {
      hosts: ['tieba.baidu.com'],
      mediaType: 'discussion',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/f/search') || path.startsWith('/hottopic')) return 'search';
        if (path.startsWith('/p/')) return 'post';
        if (path.startsWith('/home/') || path.startsWith('/f')) return 'profile';
        return 'unknown';
      },
    },
    aibase: {
      hosts: ['aibase.com'],
      mediaType: 'article',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.includes('/search')) return 'search';
        if (path.includes('/daily/') || path.includes('/news/')) return 'post';
        if (path.includes('/daily') || path === '/' || path === '/zh') return 'search';
        return 'unknown';
      },
    },
    bloomberg: {
      hosts: ['bloomberg.com'],
      mediaType: 'article',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search')) return 'search';
        if (path.includes('/news/articles/') || path.includes('/opinion/articles/')) return 'post';
        if (path.startsWith('/authors/') || path.startsWith('/profile/')) return 'profile';
        return path === '/' ? 'search' : 'unknown';
      },
    },
    dianping: {
      hosts: ['dianping.com'],
      mediaType: 'commerce',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search') || path.includes('/search/keyword/')) return 'search';
        if (path.startsWith('/shop/') || path.includes('/review/')) return 'post';
        if (path.startsWith('/member/')) return 'profile';
        return 'unknown';
      },
    },
    google: {
      hosts: ['google.com'],
      mediaType: 'search',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search')) return 'search';
        return path === '/' ? 'search' : 'unknown';
      },
    },
    'gov.cn': {
      hosts: ['gov.cn'],
      mediaType: 'article',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path, host) {
        if (host.startsWith('sousuo.')) return 'search';
        if (path.includes('/content_') || path.includes('/zhengce/') || path.includes('/yaowen/')) return 'post';
        return path === '/' || path.includes('/liebiao/') || path.includes('/index') ? 'search' : 'unknown';
      },
    },
    grok: {
      hosts: ['grok.com', 'x.ai'],
      mediaType: 'ai',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/chat') || path.startsWith('/share/')) return 'post';
        if (path.startsWith('/search')) return 'search';
        return path === '/' ? 'search' : 'unknown';
      },
    },
    hupu: {
      hosts: ['hupu.com'],
      mediaType: 'discussion',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search') || path.startsWith('/hot')) return 'search';
        if (path.includes('.html') || path.startsWith('/bbs/')) return 'post';
        if (path.startsWith('/user/')) return 'profile';
        return 'unknown';
      },
    },
    imdb: {
      hosts: ['imdb.com'],
      mediaType: 'media',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/find')) return 'search';
        if (path.startsWith('/title/')) return 'post';
        if (path.startsWith('/name/')) return 'profile';
        return path === '/' ? 'search' : 'unknown';
      },
    },
    jd: {
      hosts: ['jd.com', '360buy.com'],
      mediaType: 'product',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path, host) {
        if (host.startsWith('search.')) return 'search';
        if (host.startsWith('item.') || path.includes('/item/')) return 'post';
        if (host.endsWith('.jd.com') && host !== 'www.jd.com') return 'profile';
        return path === '/' ? 'search' : 'unknown';
      },
    },
    'linux-do': {
      hosts: ['linux.do'],
      mediaType: 'discussion',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search') || path === '/' || path.startsWith('/latest')) return 'search';
        if (path.startsWith('/t/')) return 'post';
        if (path.startsWith('/u/')) return 'profile';
        return 'unknown';
      },
    },
    v2ex: {
      hosts: ['v2ex.com'],
      mediaType: 'discussion',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search') || path === '/' || path.startsWith('/recent')) return 'search';
        if (path.startsWith('/t/')) return 'post';
        if (path.startsWith('/member/')) return 'profile';
        return 'unknown';
      },
    },
    smzdm: {
      hosts: ['smzdm.com'],
      mediaType: 'commerce',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path, host) {
        if (host.startsWith('search.') || path.startsWith('/search')) return 'search';
        if (path.includes('/p/') || path.includes('/youhui/') || path.includes('/faxian/')) return 'post';
        if (path.startsWith('/user/')) return 'profile';
        return path === '/' ? 'search' : 'unknown';
      },
    },
    taobao: {
      hosts: ['taobao.com', 'tmall.com'],
      mediaType: 'product',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path, host) {
        if (host.startsWith('s.')) return 'search';
        if (host.startsWith('item.') || path.includes('/item.htm')) return 'post';
        if (host.endsWith('.taobao.com') && host !== 'www.taobao.com') return 'profile';
        return path === '/' ? 'search' : 'unknown';
      },
    },
    wikipedia: {
      hosts: ['wikipedia.org'],
      mediaType: 'article',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/w/index.php')) return 'search';
        if (path.startsWith('/wiki/User:')) return 'profile';
        if (path.startsWith('/wiki/')) return 'post';
        return path === '/' ? 'search' : 'unknown';
      },
    },
    xianyu: {
      hosts: ['goofish.com', 'xianyu.taobao.com'],
      mediaType: 'product',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search')) return 'search';
        if (path.startsWith('/item')) return 'post';
        if (path.startsWith('/personal')) return 'profile';
        return path === '/' ? 'search' : 'unknown';
      },
    },
  };

  function compactText(value) {
    return (value || '').replace(/\s+/g, ' ').trim();
  }

  function firstText(selectors) {
    for (const selector of selectors) {
      const value = compactText(document.querySelector(selector)?.innerText || '');
      if (value) return value;
    }
    return '';
  }

  function meta(name) {
    const selectors = [
      `meta[property="${name}"]`,
      `meta[name="${name}"]`,
      `meta[itemprop="${name}"]`,
    ];
    for (const selector of selectors) {
      const value = compactText(document.querySelector(selector)?.getAttribute('content') || '');
      if (value) return value;
    }
    return '';
  }

  function pageTitle() {
    return compactText(meta('og:title') || meta('twitter:title') || document.title || firstText(['h1']));
  }

  function pageDescription() {
    return compactText(meta('og:description') || meta('description') || firstText(['article', 'main']));
  }

  function blockingNotice() {
    const text = compactText(document.body?.innerText || '');
    const patterns = [
      /次数过多/,
      /稍后再试/,
      /安全验证/,
      /验证码/,
      /请先登录/,
      /too many requests/i,
      /rate limit/i,
      /verify you are human/i,
    ];
    return patterns.some((pattern) => pattern.test(text));
  }

  function canonicalUrl() {
    return document.querySelector('link[rel="canonical"]')?.href || location.href;
  }

  function absoluteUrl(value) {
    if (!value) return '';
    try {
      return new URL(value, location.href).href;
    } catch {
      return value;
    }
  }

  function canonicalMediaType(site) {
    const type = SITE_CONFIGS[site].mediaType;
    if (type === 'video' || type === 'image') return type;
    return 'text';
  }

  function externalPostId(site, url = canonicalUrl()) {
    try {
      const parsed = new URL(url, location.href);
      const parts = parsed.pathname.split('/').filter(Boolean);
      if (site === 'bilibili') {
        const index = parts.indexOf('video');
        return index >= 0 ? parts[index + 1] || '' : '';
      }
      if (site === 'douyin') {
        const index = parts.findIndex((part) => part === 'video' || part === 'note');
        return index >= 0 ? parts[index + 1] || '' : '';
      }
      if (site === 'reddit') {
        const index = parts.indexOf('comments');
        return index >= 0 ? parts[index + 1] || '' : '';
      }
      if (site === 'zhihu') {
        if (parts[0] === 'question') return parts.slice(0, 3).join('/');
        if (parts[0] === 'p') return parts[1] || '';
      }
      if (site === 'youtube') {
        if (parts[0] === 'shorts') return parts[1] || '';
        return parsed.searchParams.get('v') || '';
      }
      if (site === 'weixin') {
        return parsed.searchParams.get('__biz') || parsed.searchParams.get('mid') || '';
      }
      if (site === 'douban') {
        const index = parts.findIndex((part) => ['subject', 'note', 'review'].includes(part));
        return index >= 0 ? parts[index + 1] || '' : '';
      }
      if (site === 'hackernews') {
        return parsed.searchParams.get('id') || '';
      }
      if (site === 'instagram') {
        const index = parts.findIndex((part) => ['p', 'reel', 'tv'].includes(part));
        return index >= 0 ? parts[index + 1] || '' : '';
      }
      if (site === 'xueqiu') {
        return parts.pop() || '';
      }
      if (site === 'eastmoney') {
        return parts.filter(Boolean).pop() || parsed.hostname;
      }
      if (site === '1688') {
        const index = parts.indexOf('offer');
        return index >= 0 ? (parts[index + 1] || '').replace('.html', '') : parsed.searchParams.get('offerId') || '';
      }
      if (site === '36kr') {
        const index = parts.indexOf('p');
        return index >= 0 ? parts[index + 1] || '' : '';
      }
      if (site === 'tieba') {
        const index = parts.indexOf('p');
        return index >= 0 ? parts[index + 1] || '' : '';
      }
      if (site === 'gov.cn') {
        return parts.pop() || parsed.hostname;
      }
      if (site === 'jd') {
        return (parts.pop() || '').replace('.html', '');
      }
      if (site === 'taobao') {
        return parsed.searchParams.get('id') || '';
      }
      if (site === 'xianyu') {
        return parsed.searchParams.get('id') || '';
      }
      if (site === 'imdb') {
        return parts[1] || '';
      }
      if (site === 'linux-do' || site === 'v2ex') {
        const index = parts.indexOf('t');
        return index >= 0 ? parts[index + 1] || '' : '';
      }
    } catch {}
    return '';
  }

  function standardMetrics(metrics = {}) {
    return {
      views: metrics.views ?? null,
      likes: metrics.likes ?? null,
      comments: metrics.comments ?? null,
      shares: metrics.shares ?? null,
      favorites: metrics.favorites ?? null,
      ...metrics,
    };
  }

  function parseMetricValue(raw) {
    if (raw === null || raw === undefined) return null;
    let text = String(raw).trim().replace(/,/g, '');
    if (!text) return null;
    const match = text.match(/([\d.]+)\s*([万亿kKmM]?)/);
    if (!match) return null;
    let value = Number(match[1]);
    if (!Number.isFinite(value)) return null;
    const unit = match[2];
    if (unit === '万') value *= 10000;
    if (unit === '亿') value *= 100000000;
    if (unit === 'k' || unit === 'K') value *= 1000;
    if (unit === 'm' || unit === 'M') value *= 1000000;
    return Math.round(value);
  }

  function findMetric(patterns) {
    const text = compactText(`${document.body?.innerText || ''} ${pageDescription()}`);
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) return parseMetricValue(match[1]);
    }
    return null;
  }

  function siteFromHost(hostname) {
    const host = hostname.toLowerCase();
    return Object.entries(SITE_CONFIGS).find(([, config]) => (
      config.hosts.some((candidate) => host === candidate || host.endsWith(`.${candidate}`))
    ))?.[0] || null;
  }

  function usefulSearchUrl(site, url) {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    const path = parsed.pathname;
    if (site === 'zhihu') {
      return path.startsWith('/question/')
        || path.startsWith('/p/')
        || path.startsWith('/people/')
        || path.startsWith('/org/');
    }
    if (site === 'bilibili') {
      return (host === 'www.bilibili.com' && (
        path.startsWith('/video/')
        || path.startsWith('/opus/')
        || path.startsWith('/bangumi/')
      )) || host === 'space.bilibili.com';
    }
    if (site === 'douyin') {
      return path.startsWith('/video/')
        || path.startsWith('/note/')
        || path.startsWith('/user/');
    }
    if (site === 'reddit') {
      return path.includes('/comments/') || path.startsWith('/r/') || path.startsWith('/user/');
    }
    if (site === 'youtube') {
      return path.startsWith('/watch') || path.startsWith('/shorts/') || path.startsWith('/@') || path.startsWith('/channel/');
    }
    if (site === 'weixin') {
      return host === 'mp.weixin.qq.com' || host === 'weixin.sogou.com';
    }
    if (site === 'douban') {
      return path.startsWith('/subject/') || path.startsWith('/note/') || path.includes('/review/') || path.startsWith('/people/');
    }
    if (site === 'hackernews') {
      return host === 'news.ycombinator.com' || host === 'hn.algolia.com';
    }
    if (site === 'instagram') {
      return path.startsWith('/p/') || path.startsWith('/reel/') || /^\/[^/]+\/?$/.test(path);
    }
    if (site === 'xueqiu' || site === 'eastmoney') {
      return true;
    }
    return true;
  }

  function currentSite() {
    return siteFromHost(location.hostname);
  }

  function getPageType(site) {
    const config = SITE_CONFIGS[site];
    if (!config) return 'unknown';
    return config.pathType(location.pathname, location.hostname);
  }

  function extractAuthor(site) {
    const ogAuthor = meta('article:author') || meta('author');
    if (ogAuthor) return ogAuthor;
    if (site === 'bilibili') {
      return firstText(['.up-name', '.username', '[class*="up-info"] a']);
    }
    if (site === 'douyin') {
      return firstText(['[data-e2e="user-name"]', '[class*="author"]']);
    }
    if (site === 'reddit') {
      const text = compactText(document.body?.innerText || '');
      const match = text.match(/u\/([A-Za-z0-9_-]+)/);
      return match ? `u/${match[1]}` : '';
    }
    if (site === 'zhihu') {
      return firstText(['.AuthorInfo-name', '[class*="AuthorInfo"] a', '[class*="author"]']);
    }
    if (site === 'youtube') {
      return firstText(['#owner #channel-name a', 'ytd-channel-name a', '[itemprop="author"] [itemprop="name"]']);
    }
    if (site === 'weixin') {
      return firstText(['#js_name', '.profile_nickname', '[class*="nickname"]']);
    }
    if (site === 'douban') {
      return firstText(['.author a', '.name', '[class*="user"] a']);
    }
    if (site === 'hackernews') {
      return firstText(['.hnuser']);
    }
    if (site === 'instagram') {
      return firstText(['header a[href^="/"]', 'article header a']);
    }
    if (site === 'xueqiu') {
      return firstText(['.user-name', '[class*="user"] a', '[class*="name"]']);
    }
    return '';
  }

  function extractPostMetrics(site) {
    if (site === 'bilibili') {
      return {
        views: findMetric([/播放量\s*([\d.,万亿kKmM]+)/, /([\d.,万亿kKmM]+)\s*(?:播放|views?)/i]),
        likes: findMetric([/点赞数\s*([\d.,万亿kKmM]+)/, /([\d.,万亿kKmM]+)\s*(?:点赞|likes?)/i]),
        comments: findMetric([/([\d.,万亿kKmM]+)\s*(?:评论|comments?)/i]),
        shares: findMetric([/转发人数\s*([\d.,万亿kKmM]+)/, /([\d.,万亿kKmM]+)\s*(?:分享|shares?)/i]),
        favorites: findMetric([/收藏人数\s*([\d.,万亿kKmM]+)/, /([\d.,万亿kKmM]+)\s*(?:收藏|favorites?)/i]),
        coins: findMetric([/投硬币枚数\s*([\d.,万亿kKmM]+)/, /([\d.,万亿kKmM]+)\s*(?:投币|coins?)/i]),
        danmaku: findMetric([/弹幕量\s*([\d.,万亿kKmM]+)/, /([\d.,万亿kKmM]+)\s*(?:弹幕|danmaku)/i]),
      };
    }
    if (site === 'douyin') {
      return {
        views: null,
        likes: findMetric([/([\d.,万亿kKmM]+)\s*(?:点赞|likes?)/i]),
        comments: findMetric([/([\d.,万亿kKmM]+)\s*(?:评论|comments?)/i]),
        shares: findMetric([/([\d.,万亿kKmM]+)\s*(?:分享|shares?)/i]),
        favorites: findMetric([/([\d.,万亿kKmM]+)\s*(?:收藏|favorites?)/i]),
      };
    }
    if (site === 'reddit') {
      return {
        score: findMetric([/([\d.,kKmM]+)\s*(?:upvotes?|points?)/i]),
        comments: findMetric([/([\d.,kKmM]+)\s*(?:comments?)/i]),
      };
    }
    if (site === 'zhihu') {
      return {
        likes: findMetric([/([\d.,万亿kKmM]+)\s*(?:赞同|点赞)/]),
        comments: findMetric([/([\d.,万亿kKmM]+)\s*(?:评论)/]),
        favorites: findMetric([/([\d.,万亿kKmM]+)\s*(?:收藏)/]),
      };
    }
    if (site === 'youtube') {
      return {
        views: findMetric([/([\d.,万亿kKmM]+)\s*(?:次观看|views?)/i]),
        likes: findMetric([/([\d.,万亿kKmM]+)\s*(?:likes?|点赞)/i]),
        comments: findMetric([/([\d.,万亿kKmM]+)\s*(?:comments?|评论)/i]),
      };
    }
    if (site === 'instagram') {
      return {
        likes: findMetric([/([\d.,万亿kKmM]+)\s*(?:likes?|赞)/i]),
        comments: findMetric([/([\d.,万亿kKmM]+)\s*(?:comments?|评论)/i]),
      };
    }
    if (site === 'hackernews') {
      return {
        score: findMetric([/([\d.,kKmM]+)\s*(?:points?)/i]),
        comments: findMetric([/([\d.,kKmM]+)\s*(?:comments?)/i]),
      };
    }
    return {};
  }

  function extractProfileMetrics(site) {
    if (site === 'reddit') {
      return {
        followers: findMetric([/([\d.,kKmM]+)\s*(?:followers?)/i]),
        following: null,
        karma: findMetric([/([\d.,kKmM]+)\s*(?:karma)/i]),
        postsCount: null,
      };
    }
    if (site === 'hackernews') {
      return {
        karma: findMetric([/karma:\s*([\d.,kKmM]+)/i]),
        followers: null,
        following: null,
        postsCount: null,
      };
    }
    return {
      followers: findMetric([/([\d.,万亿kKmM]+)\s*(?:粉丝|followers?)/i]),
      following: findMetric([/([\d.,万亿kKmM]+)\s*(?:关注|following)/i]),
      likes: findMetric([/([\d.,万亿kKmM]+)\s*(?:获赞|点赞|likes?)/i]),
      postsCount: findMetric([/([\d.,万亿kKmM]+)\s*(?:作品|投稿|posts?)/i]),
    };
  }

  function extractHackernewsSearchItems() {
    const items = [];
    const rows = document.querySelectorAll('.Story');
    for (const row of rows) {
      if (items.length >= 20) break;
      const titleLink = row.querySelector('.Story_title a') || row.querySelector('a[href]');
      if (!titleLink) continue;
      const title = compactText(titleLink.innerText || '');
      if (!title || title.length < 3) continue;
      const storyLink = titleLink.getAttribute('href') || '';
      let url = storyLink;
      if (storyLink.startsWith('item?id=')) {
        url = 'https://news.ycombinator.com/' + storyLink;
      }
      const meta = row.querySelector('.Story_meta') || row;
      const metaText = compactText(meta.innerText || '');
      const pointsMatch = metaText.match(/(\d+)\s*(?:point|point[s]?)/i);
      const commentsMatch = metaText.match(/(\d+)\s*comment/i);
      const authorLink = row.querySelector('a[href*="user?id="]');
      items.push({
        title,
        url,
        author: authorLink ? compactText(authorLink.innerText || '') : null,
        publishedAt: null,
        metrics: standardMetrics({
          score: pointsMatch ? parseInt(pointsMatch[1], 10) : null,
          comments: commentsMatch ? parseInt(commentsMatch[1], 10) : null,
        }),
        snippet: '',
        mediaType: 'text',
      });
    }
    return items;
  }

  function extractBilibiliHotItems() {
    const items = [];
    const cards = document.querySelectorAll('.video-card, .rank-item, .video-card-wrap, .bili-video-card');
    for (const card of cards) {
      if (items.length >= 50) break;
      const titleEl = card.querySelector('.video-name, .video-card__info [title], .video-card__info a, .info a, a.title, .bili-video-card__info a');
      if (!titleEl) continue;
      const title = compactText(titleEl.innerText || titleEl.getAttribute('title') || '');
      if (!title || title.length < 2) continue;
      const linkEl = card.querySelector('a[href*="/video/BV"], a[href*="bilibili.com/video/BV"]') || titleEl.closest('a[href]');
      let url = '';
      try {
        url = new URL(linkEl?.getAttribute('href') || titleEl.getAttribute('href') || '', location.origin).href;
      } catch { continue; }
      const authorEl = card.querySelector('.up-name, .video-card__info .up-name, .author, .bili-video-card__info--author');
      const viewEl = card.querySelector('.play-text, .view-text, .bili-video-card__stats--item');
      const danmakuEl = card.querySelector('.dm-text, .bili-video-card__stats--item:nth-child(2)');
      const lines = (card.innerText || '').split('\n').map(compactText).filter(Boolean);
      const fallbackAuthor = lines.length >= 3 ? lines[lines.length - 3] : null;
      const fallbackViews = lines.length >= 2 ? lines[lines.length - 2] : null;
      const fallbackDanmaku = lines.length >= 1 ? lines[lines.length - 1] : null;
      items.push({
        title,
        url,
        author: authorEl ? compactText(authorEl.innerText || '') : fallbackAuthor,
        publishedAt: null,
        metrics: standardMetrics({
          views: parseMetricValue(viewEl ? compactText(viewEl.innerText || '') : fallbackViews),
          likes: null,
          comments: null,
          favorites: null,
          danmaku: parseMetricValue(danmakuEl ? compactText(danmakuEl.innerText || '') : fallbackDanmaku),
        }),
        snippet: '',
        mediaType: 'video',
      });
    }
    return items;
  }

  function normalizedSearchResultUrl(site, href) {
    const parsed = new URL(href, location.href);
    if (site === 'google' && parsed.hostname.includes('google.') && parsed.pathname === '/url') {
      const target = parsed.searchParams.get('q') || parsed.searchParams.get('url');
      if (target) return new URL(target, location.href).href;
    }
    return parsed.href;
  }

  function extractSearchItems(site) {
    const seen = new Set();
    const items = [];
    const anchors = Array.from(document.querySelectorAll('a[href]'));
    for (const anchor of anchors) {
      if (items.length >= 20) break;
      const title = compactText(anchor.innerText || anchor.getAttribute('aria-label') || '');
      if (!title || title.length < 4) continue;
      if (/^[\d.,万亿kKmM\s:]+$/.test(title)) continue;
      let url = '';
      try {
        url = normalizedSearchResultUrl(site, anchor.getAttribute('href'));
      } catch {
        continue;
      }
      const itemSite = siteFromHost(new URL(url).hostname);
      if (site === 'google') {
        if (new URL(url).hostname.includes('google.')) continue;
      } else if (itemSite !== site) {
        continue;
      }
      if (!usefulSearchUrl(site, url)) continue;
      const key = url;
      if (seen.has(key)) continue;
      seen.add(key);
      items.push({
        title,
        url,
        author: null,
        publishedAt: null,
        metrics: standardMetrics({}),
        snippet: '',
        mediaType: canonicalMediaType(site),
      });
    }
    return items;
  }

  function readPost(site, pageType) {
    const mediaType = SITE_CONFIGS[site].mediaType;
    const url = canonicalUrl();
    const authorName = extractAuthor(site);
    return {
      ok: true,
      mode: 'semantic',
      kind: 'read_post',
      pageType,
      content: {
        url,
        externalPostId: externalPostId(site, url),
        title: pageTitle(),
        author: {
          id: null,
          nickname: authorName,
          profileUrl: null,
        },
        publishedAt: null,
        description: pageDescription(),
        mediaType: canonicalMediaType(site),
        videoContentParsed: mediaType === 'video' ? false : null,
        cover: absoluteUrl(meta('og:image') || meta('twitter:image') || ''),
        metrics: standardMetrics(extractPostMetrics(site)),
        rawPayload: {
          pageType,
          sourceMediaType: mediaType,
        },
      },
    };
  }

  function readProfile(site, pageType) {
    return {
      ok: true,
      mode: 'semantic',
      kind: 'read_profile_metrics',
      pageType,
      content: {
        url: canonicalUrl(),
        profileId: location.pathname.split('/').filter(Boolean).pop() || '',
        nickname: pageTitle(),
        description: pageDescription(),
        metrics: extractProfileMetrics(site),
        recentPosts: extractSearchItems(site).slice(0, 12),
        rawPayload: {
          pageType,
        },
      },
    };
  }

  async function readSearch(site, pageType, params = {}) {
    const notice = blockingNotice();
    if (site === 'hackernews') {
      const keyword = params.keyword || new URLSearchParams(location.search).get('q') || '';
      const limit = Math.min(Math.max(Number(params.limit || params.targetCount || 20) || 20, 1), 20);
      const items = extractHackernewsSearchItems().slice(0, limit);
      return {
        ok: true,
        mode: 'semantic',
        kind: 'search',
        pageType,
        content: {
          url: location.href,
          keyword,
          items,
          rawPayload: {
            pageType,
            itemCount: items.length,
            source: 'page-dom',
            needsHumanAttention: notice,
          },
        },
      };
    }
    const items = extractSearchItems(site);
    return {
      ok: true,
      mode: 'semantic',
      kind: 'search',
      pageType,
      content: {
        url: location.href,
        keyword: params.keyword || new URLSearchParams(location.search).get('q') || new URLSearchParams(location.search).get('keyword') || '',
        items,
        rawPayload: {
          pageType,
          itemCount: items.length,
          needsHumanAttention: notice,
        },
      },
    };
  }

  async function readHot(site, pageType, params = {}) {
    const mediaType = canonicalMediaType(site);
    if (site === 'bilibili') {
      const limit = Math.min(Math.max(Number(params.limit || params.targetCount || 20) || 20, 1), 50);
      const items = extractBilibiliHotItems().slice(0, limit);
      return {
        ok: true,
        mode: 'semantic',
        kind: 'read_hot',
        pageType,
        content: {
          url: location.href,
          items,
          rawPayload: {
            pageType,
            itemCount: items.length,
            source: 'page-dom',
            videoContentParsed: false,
            sourceMediaType: mediaType,
          },
        },
      };
    }
    const items = extractSearchItems(site);
    return {
      ok: true,
      mode: 'semantic',
      kind: 'read_hot',
      pageType,
      content: {
        url: location.href,
        items,
        rawPayload: {
          pageType,
          itemCount: items.length,
          source: 'page-links',
          videoContentParsed: false,
          sourceMediaType: mediaType,
        },
      },
    };
  }

  function readAccountStatus(site, pageType) {
    const text = compactText(document.body?.innerText || '');
    const loginHints = /log in|sign in|登录|扫码|验证码|请先登录|Log in|Sign in/.test(text);
    const notice = blockingNotice();
    const accountText = extractAuthor(site) || firstText([
      '[aria-label*="Account"]',
      '[aria-label*="Profile"]',
      '[class*="avatar"]',
      '[class*="user"]',
    ]);
    return {
      ok: true,
      mode: 'semantic',
      kind: 'account_status',
      pageType,
      content: {
        url: location.href,
        loggedIn: loginHints ? false : null,
        needsHumanLogin: loginHints,
        account: accountText ? { displayName: accountText } : null,
        rawPayload: {
          pageType,
          loginHints,
          needsHumanAttention: notice,
        },
      },
    };
  }

  function createAdapter(site) {
    return {
      site,
      match() {
        return currentSite() === site;
      },
      capabilities() {
        return {
          site,
          read: SITE_CONFIGS[site].read,
          action: [],
          workflow: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
        };
      },
      getPageType() {
        return getPageType(site);
      },
      collect(base) {
        const pageType = getPageType(site);
        const notice = blockingNotice();
        return {
          ...base,
          site,
          signals: {
            ...base.signals,
            ready: base.signals.ready || Boolean(pageTitle()) || notice,
            pageType,
            mediaType: SITE_CONFIGS[site].mediaType,
            needsHumanAttention: notice,
          },
          content: {
            ...base.content,
            title: pageTitle(),
            description: pageDescription(),
            needsHumanAttention: notice,
          },
        };
      },
      probeReady(context) {
        const pageType = getPageType(site);
        return {
          ...this.collect(context.baseSnapshot),
          pageType,
        };
      },
      async read(kind, params = {}) {
        const pageType = getPageType(site);
        if (kind === 'read_post') return readPost(site, pageType);
        if (kind === 'read_profile_metrics') return readProfile(site, pageType);
        if (kind === 'search') return readSearch(site, pageType, params);
        if (kind === 'read_hot') return readHot(site, pageType, params);
        if (kind === 'account_status') return readAccountStatus(site, pageType);
        return {
          ok: false,
          mode: 'semantic',
          kind,
          pageType,
          error: `Unsupported read kind: ${kind}`,
        };
      },
    };
  }

  for (const site of Object.keys(SITE_CONFIGS)) {
    window.BrowserBridgeAdapters.push(createAdapter(site));
  }
})();
