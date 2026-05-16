(function registerMediaAdapters() {
  window.BrowserBridgeAdapters = window.BrowserBridgeAdapters || [];

  const SITE_CONFIGS = {
    zhihu: {
      hosts: ['zhihu.com'],
      mediaType: 'article',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search')) return 'search';
        if (path.startsWith('/people/') || path.startsWith('/org/')) return 'profile';
        if (path.startsWith('/question/') || path.startsWith('/p/') || path.includes('/answer/')) return 'post';
        return 'unknown';
      },
    },
    bilibili: {
      hosts: ['bilibili.com', 'b23.tv'],
      mediaType: 'video',
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path, host) {
        if (host === 'search.bilibili.com' || path.startsWith('/all')) return 'search';
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
      read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
      pathType(path) {
        if (path.startsWith('/search')) return 'search';
        if (path.startsWith('/user/')) return 'profile';
        if (path.includes('/comments/')) return 'post';
        if (path.startsWith('/r/')) return 'profile';
        return 'unknown';
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
    return SITE_CONFIGS[site].mediaType === 'video' ? 'video' : 'text';
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
      return path.startsWith('/r/') || path.startsWith('/user/');
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
    return {
      followers: findMetric([/([\d.,万亿kKmM]+)\s*(?:粉丝|followers?)/i]),
      following: findMetric([/([\d.,万亿kKmM]+)\s*(?:关注|following)/i]),
      likes: findMetric([/([\d.,万亿kKmM]+)\s*(?:获赞|点赞|likes?)/i]),
      postsCount: findMetric([/([\d.,万亿kKmM]+)\s*(?:作品|投稿|posts?)/i]),
    };
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
        url = new URL(anchor.getAttribute('href'), location.href).href;
      } catch {
        continue;
      }
      const itemSite = siteFromHost(new URL(url).hostname);
      if (itemSite !== site) continue;
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

  function readSearch(site, pageType, params = {}) {
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
        return {
          ...base,
          site,
          signals: {
            ...base.signals,
            ready: base.signals.ready || Boolean(pageTitle()),
            pageType,
            mediaType: SITE_CONFIGS[site].mediaType,
          },
          content: {
            ...base.content,
            title: pageTitle(),
            description: pageDescription(),
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
