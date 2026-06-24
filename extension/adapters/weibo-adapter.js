// Weibo Adapter for Browser Bridge

function getWeiboHost() {
  return (location.hostname || '').toLowerCase();
}

function isWeiboMainHost() {
  const host = getWeiboHost();
  return host === 'weibo.com' || host.endsWith('.weibo.com');
}

function isWeiboSearchHost() {
  return getWeiboHost() === 's.weibo.com';
}

function isWeiboMobileHost() {
  return getWeiboHost() === 'm.weibo.cn';
}

function isWeiboShareHost() {
  return getWeiboHost() === 'mapp.api.weibo.cn';
}

function normalizeWeiboUrl(url) {
  if (!url) return '';
  try {
    const parsed = new URL(url, location.origin);
    return `${parsed.origin}${parsed.pathname}`;
  } catch {
    return url;
  }
}

function isWeiboPostUrl(url) {
  if (!url) return false;
  try {
    const parsed = new URL(url, location.origin);
    const host = (parsed.hostname || '').toLowerCase();
    const parts = parsed.pathname.split('/').filter(Boolean);
    if ((host === 'm.weibo.cn' || host.endsWith('.m.weibo.cn')) && parts.length >= 2 && parts[0] === 'status') {
      return true;
    }
    if (host === 'weibo.com' || host.endsWith('.weibo.com')) {
      if (parts.length >= 2 && /^\d+$/.test(parts[0]) && !['hot', 'u', 'n', 'p'].includes(parts[1])) {
        return true;
      }
    }
  } catch {}
  return false;
}

function looksLikeTimeText(text) {
  const val = (text || '').trim();
  if (!val) return false;
  return /(\d{1,2}-\d{1,2})|(今天|昨天)|(\d+分钟前)|(\d+小时前)|(\d{2,4}年\d{1,2}月\d{1,2}日)/.test(val);
}

function getWeiboPageType() {
  const host = getWeiboHost();
  const path = location.pathname || '';
  const parts = path.split('/').filter(Boolean);

  if (isWeiboSearchHost() && path.startsWith('/weibo')) return 'search';
  if (isWeiboMobileHost() && parts.length >= 2 && parts[0] === 'status') return 'post';
  if (isWeiboShareHost()) return 'other';
  if ((host === 'weibo.com' || host === 'www.weibo.com') && path === '/') return 'home';
  if ((host === 'weibo.com' || host === 'www.weibo.com') && path.startsWith('/hot/search')) return 'hot_search';
  if ((host === 'weibo.com' || host === 'www.weibo.com') && path.startsWith('/hot/weibo/')) return 'hot_feed';
  if ((host === 'weibo.com' || host === 'www.weibo.com') && (path.startsWith('/u/') || path.startsWith('/n/'))) return 'profile';
  if ((host === 'weibo.com' || host === 'www.weibo.com') && parts.length >= 2 && /^\d+$/.test(parts[0])) return 'post';
  if ((document.title || '').includes('微博正文')) return 'post';
  return 'other';
}

function splitLines(text) {
  return (text || '')
    .split('\n')
    .map((line) => line.replace(/\s+/g, ' ').trim())
    .filter(Boolean);
}

function isHeaderNoise(line) {
  const val = (line || '').trim();
  if (!val) return true;
  if (['微博正文', '返回', '公开', '关注', '推荐', '热门', 'c'].includes(val)) return true;
  if (/^\d+人关注了/.test(val)) return true;
  if (/^来自 /.test(val) || /^发布于 /.test(val)) return true;
  if (/^已编辑$/.test(val)) return true;
  if (/^粉丝：/.test(val)) return true;
  return false;
}

function isFooterBoundary(line) {
  const val = (line || '').trim();
  if (!val) return false;
  return [
    '分享这条博文',
    '同时转发',
    '评论',
    '按热度',
    '按时间',
    '微博热搜',
    '你可能感兴趣的人',
    '帮助中心',
    '发表评论',
    '没有更多内容了',
    '查看完整热搜榜单',
  ].includes(val);
}

function isSkippableContentLine(line) {
  const val = (line || '').trim();
  if (!val) return true;
  if (['播放视频', '点赞是美意，赞赏是鼓励', '为TA助威', 'Live'].includes(val)) return true;
  if (/^\+?\d+$/.test(val)) return false;
  if (/^\d{2}:\d{2}$/.test(val)) return true;
  if (/^\d+(\.\d+)?万?次观看$/.test(val)) return true;
  return false;
}

function isCountLike(line) {
  return /^(\d+|\d+\.\d+万|转发\d+评论|\d+赞\d+)$/.test((line || '').trim());
}

function extractEngagement(lines) {
  const cleaned = (lines || []).map((line) => line.trim()).filter(Boolean);
  const counts = cleaned.filter((line) => /^(\d+|\d+\.\d+万)$/.test(line));
  if (counts.length >= 3) {
    const last3 = counts.slice(-3);
    return {
      reposts: last3[0],
      comments: last3[1],
      likes: last3[2],
    };
  }
  const joined = cleaned.join(' ');
  const mobileMatch = joined.match(/转发\s*(\d+)\s*评论\s*(\d+)\s*(\d+)\s*赞/);
  if (mobileMatch) {
    return {
      reposts: mobileMatch[1],
      comments: mobileMatch[2],
      likes: mobileMatch[3],
    };
  }
  const compactMatch = joined.match(/转发(\d+)评论\s*(\d+)赞(\d+)/);
  if (compactMatch) {
    return {
      reposts: compactMatch[1],
      comments: compactMatch[2],
      likes: compactMatch[3],
    };
  }
  return {};
}

function engagementToMetrics(engagement = {}) {
  return {
    reposts: engagement.reposts ?? null,
    comments: engagement.comments ?? null,
    likes: engagement.likes ?? null,
  };
}

function isWeiboAdOrRecommendationText(text) {
  return /(广告|推广|推荐|你可能感兴趣|热门微博|微博热搜|查看完整热搜榜单)/.test(text || '');
}

function extractCommentMetricsFromText(text) {
  const likeMatch = (text || '').match(/(?:赞|点赞)\s*([\d.,万亿kKmM]+)|([\d.,万亿kKmM]+)\s*(?:赞|点赞)/);
  const replyMatch = (text || '').match(/(?:回复|评论)\s*([\d.,万亿kKmM]+)|([\d.,万亿kKmM]+)\s*(?:回复|评论)/);
  return {
    likes: likeMatch ? (likeMatch[1] || likeMatch[2]) : null,
    comments: null,
    replies: replyMatch ? (replyMatch[1] || replyMatch[2]) : null,
  };
}

function normalizeCommentLimit(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 20;
  return Math.min(Math.max(Math.floor(parsed), 0), 100);
}

function detectCommentsUnavailableReason(root) {
  const text = (root?.innerText || document.body?.innerText || '').trim();
  if (!text) return 'not_loaded';
  if (/评论加载失败|评论暂时无法显示|无法查看评论|登录后查看评论/.test(text)) return 'not_loaded';
  return null;
}

function extractVisibleComments(root, limit = 20) {
  limit = normalizeCommentLimit(limit);
  if (limit <= 0) return [];
  const seen = new Set();
  const candidates = Array.from((root || document).querySelectorAll('[class*="comment"], [class*="Comment"], .card-comment'))
    .concat(Array.from(document.querySelectorAll('[class*="comment"], [class*="Comment"], .card-comment')));
  const comments = [];
  for (const el of candidates) {
    if (comments.length >= limit) break;
    const lines = splitLines(el.innerText || '');
    const text = lines
      .filter((line) => !isFooterBoundary(line))
      .filter((line) => !/^(评论|按热度|按时间|发表评论)$/.test(line))
      .join('\n')
      .trim();
    if (!text || text.length < 2 || text.length > 800) continue;
    if (isWeiboAdOrRecommendationText(text)) continue;
    const key = text.slice(0, 120);
    if (seen.has(key)) continue;
    seen.add(key);
    const author = lines.find((line) => !looksLikeTimeText(line) && !/^(回复|赞|评论)$/.test(line)) || null;
    const time = lines.find((line) => looksLikeTimeText(line)) || null;
    comments.push({
      authorName: author,
      time,
      text,
      media: [],
      metrics: extractCommentMetricsFromText(text),
      platformMetrics: {},
    });
  }
  return comments;
}

function extractReadableBody(lines, author, publishedAt) {
  const result = [];
  let started = false;
  const expectedTime = (publishedAt || '').trim();
  const expectedAuthor = (author || '').trim();

  for (const line of lines || []) {
    const val = (line || '').trim();
    if (!val) continue;

    if (!started) {
      if (expectedAuthor && val === expectedAuthor) continue;
      if (expectedTime && val === expectedTime) {
        started = true;
        continue;
      }
      if (isHeaderNoise(val)) continue;
      started = true;
    }

    if (isFooterBoundary(val)) break;
    if (isSkippableContentLine(val)) continue;
    result.push(val);
  }

  while (result.length && (isCountLike(result[result.length - 1]) || isFooterBoundary(result[result.length - 1]))) {
    result.pop();
  }
  return result.join('\n').trim();
}

function dedupStrings(values) {
  return Array.from(new Set((values || []).filter(Boolean)));
}

function isUsefulImageUrl(src, cls = '') {
  const url = (src || '').trim();
  if (!/^https?:/i.test(url)) return false;
  if (/tvax\d*\.sinaimg\.cn/i.test(url)) return false;
  if (/face\.t\.sinajs\.cn/i.test(url)) return false;
  if (/h5\.sinaimg\.cn\/upload/i.test(url)) return false;
  if (/simg\.s\.weibo\.com/i.test(url)) return false;
  if (/default_avatar/i.test(url)) return false;
  if (/woo-icon-vipimg/i.test(cls || '')) return false;
  return /wx\d+\.sinaimg\.cn|ww\d+\.sinaimg\.cn/i.test(url) || /woo-picture-img|picture-cover|pic-region|img_box/i.test(cls || '');
}

function collectImageUrls(root) {
  return dedupStrings(Array.from((root || document).querySelectorAll('img'))
    .map((img) => ({ src: img.currentSrc || img.src || '', cls: img.className || '' }))
    .filter((item) => isUsefulImageUrl(item.src, item.cls))
    .map((item) => item.src));
}

function collectVideoUrls(root) {
  const videos = [];
  for (const video of Array.from((root || document).querySelectorAll('video'))) {
    const src = video.currentSrc || video.src || '';
    if (src && /^https?:/i.test(src)) {
      videos.push(src);
    }
  }
  for (const link of Array.from((root || document).querySelectorAll('a[href*="video.weibo.com/show"]'))) {
    if (link.href) videos.push(link.href);
  }
  return dedupStrings(videos);
}

function appendMediaMarkers(text, images, videos) {
  const parts = [];
  if (text) parts.push(text);
  for (const url of images || []) {
    parts.push(`[Image: ${url}]`);
  }
  for (const url of videos || []) {
    parts.push(`[Video: ${url}]`);
  }
  return parts.filter(Boolean).join('\n\n').trim();
}

function pickAuthorLink(root) {
  return Array.from((root || document).querySelectorAll('a[href]')).find((a) => {
    const href = a.href || '';
    return href.includes('/u/') && (a.innerText || '').trim();
  }) || null;
}

function pickPostLink(root) {
  const links = Array.from((root || document).querySelectorAll('a[href]')).filter((a) => isWeiboPostUrl(a.href));
  return links.find((a) => looksLikeTimeText(a.innerText || '')) || links[0] || null;
}

function extractFeedItem(el) {
  const lines = splitLines(el.innerText || '');
  const authorLink = pickAuthorLink(el);
  const postLink = pickPostLink(el);
  const author = (authorLink?.innerText || '').trim();
  const publishedAt = (postLink?.innerText || '').trim();
  const images = collectImageUrls(el);
  const videos = collectVideoUrls(el);
  const text = appendMediaMarkers(extractReadableBody(lines, author, publishedAt), images, videos);
  const engagement = extractEngagement(lines);

  return {
    author,
    publishedAt,
    text,
    url: normalizeWeiboUrl(postLink?.href || ''),
    images,
    videos,
    engagement,
  };
}

function extractFlowItems() {
  return Array.from(document.querySelectorAll('.wbpro-scroller-item'))
    .map((el) => extractFeedItem(el))
    .filter((item) => item.author && item.url && item.text);
}

function extractHotSearchItems() {
  return Array.from(document.querySelectorAll('.wbpro-scroller-item'))
    .map((el) => {
      const lines = splitLines(el.innerText || '');
      const url = Array.from(el.querySelectorAll('a[href]')).map((a) => a.href).find(Boolean) || '';
      if (!lines.length || !url) return null;

      let cursor = 0;
      let rank = null;
      if (/^\d+$/.test(lines[cursor] || '')) {
        rank = lines[cursor];
        cursor += 1;
      }
      const keyword = lines[cursor] || '';
      cursor += 1;
      let label = null;
      if (['热', '新', '火热', '首发'].includes(lines[cursor] || '')) {
        label = lines[cursor];
        cursor += 1;
      }
      const hotValue = /^\d+$/.test(lines[cursor] || '') ? lines[cursor] : null;
      const isAd = !rank && !hotValue;
      return {
        rank,
        keyword,
        label,
        hotValue,
        url,
        isAd,
      };
    })
    .filter((item) => item && item.keyword && !item.isAd);
}

function extractSearchCard(el) {
  const lines = splitLines(el.innerText || '');
  const authorLink = Array.from(el.querySelectorAll('a[href]')).find((a) => (a.className || '').includes('name')) || pickAuthorLink(el);
  const postLink = pickPostLink(el);
  const author = (authorLink?.innerText || '').trim();
  const publishedAt = (postLink?.innerText || '').trim();
  const textRoot = el.querySelector('.txt') || el;
  const images = collectImageUrls(el);
  const videos = collectVideoUrls(el);
  const text = appendMediaMarkers(extractReadableBody(splitLines(textRoot.innerText || ''), author, publishedAt), images, videos);
  return {
    author,
    publishedAt,
    text,
    url: normalizeWeiboUrl(postLink?.href || ''),
    images,
    videos,
    engagement: extractEngagement(lines),
  };
}

function extractSearchItems() {
  return Array.from(document.querySelectorAll('.card-wrap'))
    .map((el) => extractSearchCard(el))
    .filter((item) => item.url && item.text);
}

function findPcDetailRoot() {
  const postLink = pickPostLink(document);
  let node = postLink;
  while (node && node !== document.body) {
    const text = (node.innerText || '').trim();
    if (text.includes('分享这条博文') || text.includes('同时转发')) {
      return node;
    }
    node = node.parentElement;
  }
  return Array.from(document.querySelectorAll('div,section,article')).find((el) => {
    const text = (el.innerText || '').trim();
    return text.includes('分享这条博文') && text.includes('同时转发');
  }) || null;
}

function extractPcPost(commentLimit = 20) {
  const root = findPcDetailRoot() || document.body;
  const lines = splitLines(root.innerText || '');
  const authorLink = pickAuthorLink(root);
  const postLink = pickPostLink(root);
  const author = (authorLink?.innerText || '').trim();
  const publishedAt = (postLink?.innerText || '').trim();
  const images = collectImageUrls(root);
  const videos = collectVideoUrls(root);
  const text = appendMediaMarkers(extractReadableBody(lines, author, publishedAt), images, videos);
  const engagement = extractEngagement(lines);
  const comments = extractVisibleComments(root, commentLimit);
  return {
    author,
    publishedAt,
    text,
    url: normalizeWeiboUrl(postLink?.href || location.href),
    images,
    videos,
    engagement,
    metrics: engagementToMetrics(engagement),
    comments,
    commentsUnavailableReason: comments.length ? null : detectCommentsUnavailableReason(root),
  };
}

function extractMobilePost(commentLimit = 20) {
  const root = Array.from(document.querySelectorAll('.card-wrap')).find((el) => {
    const text = (el.innerText || '').trim();
    return text.includes('评论') && text.includes('赞');
  }) || document.body;
  const lines = splitLines(root.innerText || '').filter((line) => line !== '微博正文');
  const author = lines[0] || '';
  const publishedAt = lines[1] || '';
  const images = collectImageUrls(root);
  const videos = collectVideoUrls(root);
  const text = appendMediaMarkers(extractReadableBody(lines.slice(2), '', ''), images, videos);
  const engagement = extractEngagement(lines);
  const comments = extractVisibleComments(root, commentLimit);
  return {
    author,
    publishedAt,
    text,
    url: normalizeWeiboUrl(location.href),
    images,
    videos,
    engagement,
    metrics: engagementToMetrics(engagement),
    comments,
    commentsUnavailableReason: comments.length ? null : detectCommentsUnavailableReason(root),
  };
}

function extractCurrentPost(commentLimit = 20) {
  if (isWeiboMobileHost()) {
    return extractMobilePost(commentLimit);
  }
  return extractPcPost(commentLimit);
}

function getSearchKeyword() {
  try {
    const params = new URLSearchParams(location.search);
    return (params.get('q') || '').trim();
  } catch {
    return '';
  }
}

function parseWeiboMetricValue(raw) {
  if (raw === null || raw === undefined) return null;
  const text = String(raw).replace(/,/g, '').trim();
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

function findWeiboMetric(labels) {
  const text = document.body?.innerText || '';
  for (const label of labels) {
    const pattern = new RegExp(`${label}\\s*[:：]?\\s*([\\d.,万亿kKmM]+)|([\\d.,万亿kKmM]+)\\s*${label}`, 'i');
    const match = text.match(pattern);
    if (match) return parseWeiboMetricValue(match[1] || match[2]);
  }
  return null;
}

function extractProfileMetrics() {
  const pathParts = location.pathname.split('/').filter(Boolean);
  const profileId = pathParts[pathParts.length - 1] || '';
  const titleName = (document.title || '').split('的微博')[0].replace(/微博.*$/, '').trim();
  const nickname = titleName || splitLines(document.body?.innerText || '')[0] || '';
  return {
    url: normalizeWeiboUrl(location.href),
    profileId,
    nickname,
    metrics: {
      followers: findWeiboMetric(['粉丝', 'followers']),
      following: findWeiboMetric(['关注', 'following']),
      postsCount: findWeiboMetric(['微博', 'posts']),
      likes: findWeiboMetric(['获赞', '点赞', 'likes']),
    },
    recentPosts: extractFlowItems().slice(0, 12),
    rawPayload: {
      pageType: getWeiboPageType(),
    },
  };
}

const weiboAdapter = {
  id: 'weibo',
  match() {
    return isWeiboMainHost() || isWeiboSearchHost() || isWeiboMobileHost() || isWeiboShareHost();
  },
  getPageType() {
    return getWeiboPageType();
  },
  capabilities() {
    return {
      read: ['read_home', 'read_hot_feed', 'read_hot_search', 'read_post', 'search', 'read_profile_metrics', 'account_status'],
      act: [],
    };
  },
  collect(baseSnapshot) {
    const pageType = getWeiboPageType();
    const flowItems = pageType === 'home' || pageType === 'hot_feed' ? extractFlowItems() : [];
    const hotSearchItems = pageType === 'hot_search' ? extractHotSearchItems() : [];
    const searchItems = pageType === 'search' ? extractSearchItems() : [];
    const post = pageType === 'post' ? extractCurrentPost() : null;
    const profile = pageType === 'profile' ? extractProfileMetrics() : null;
    const ready = !!(
      document.readyState === 'complete' && (
        ((pageType === 'home' || pageType === 'hot_feed') && flowItems.length > 0) ||
        (pageType === 'hot_search' && hotSearchItems.length > 0) ||
        (pageType === 'search' && searchItems.length > 0) ||
        (pageType === 'profile' && profile && document.body.innerText.length > 100) ||
        (pageType === 'post' && post && ((post.text || '').length > 10 || (post.images || []).length > 0 || (post.videos || []).length > 0))
      )
    );

    return {
      site: 'weibo',
      page: baseSnapshot.page,
      signals: {
        ...baseSnapshot.signals,
        pageType,
        isWeibo: true,
        ready,
        flowItemCount: flowItems.length,
        hotSearchCount: hotSearchItems.length,
        searchCount: searchItems.length,
        hasPost: !!post,
        hasProfile: !!profile,
        searchKeyword: pageType === 'search' ? getSearchKeyword() : null,
      },
      content: {
        items: flowItems.length ? flowItems : (pageType === 'hot_search' ? hotSearchItems : searchItems),
        post,
        profile,
      },
    };
  },
  async probeReady(context) {
    const snap = this.collect(context.baseSnapshot);
    return {
      ok: true,
      site: snap.site,
      page: snap.page,
      signals: snap.signals,
      content: snap.content,
    };
  },
  async read(kind, _params, context) {
    const snap = this.collect(context.baseSnapshot);
    if (kind === 'read_home' || kind === 'read_hot_feed' || kind === 'read_hot_search' || kind === 'search') {
      return {
        ok: true,
        mode: 'semantic',
        kind,
        page: snap.page,
        signals: snap.signals,
        content: {
          items: snap.content.items || [],
          keyword: snap.signals.searchKeyword || null,
        },
      };
    }
    if (kind === 'read_post') {
      const commentLimit = normalizeCommentLimit(_params?.commentLimit);
      return {
        ok: true,
        mode: 'semantic',
        kind,
        page: snap.page,
        signals: snap.signals,
        content: extractCurrentPost(commentLimit),
      };
    }
    if (kind === 'read_profile_metrics') {
      return {
        ok: true,
        mode: 'semantic',
        kind,
        page: snap.page,
        signals: snap.signals,
        content: snap.content.profile || {},
      };
    }
    return {
      ok: false,
      kind,
      page: snap.page,
      signals: snap.signals,
      error: `Unsupported read kind: ${kind}`,
    };
  },
  async act(kind, _params, context) {
    const snap = this.collect(context.baseSnapshot);
    return {
      ok: false,
      action: kind,
      page: snap.page,
      signals: snap.signals,
      error: 'No actions implemented for weibo',
    };
  },
  async verify(_kind, _params, _context, actionResult) {
    return {
      ok: true,
      verified: !!actionResult?.ok,
      actionResult,
    };
  },
};

window.BrowserBridgeAdapters = window.BrowserBridgeAdapters || [];
window.BrowserBridgeAdapters.push(weiboAdapter);
