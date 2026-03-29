// Xiaohongshu Adapter for Browser Bridge

function isXiaohongshuHost() {
  return location.hostname.includes('xiaohongshu.com');
}

function getXiaohongshuPageType() {
  const path = location.pathname || '';
  if (/^\/explore\/[A-Za-z0-9]+/.test(path)) return 'post';
  if (path === '/explore') return 'home';
  if (path.startsWith('/search_result')) return 'search';
  return 'other';
}

function normalizeXiaohongshuUrl(url) {
  if (!url) return '';
  try {
    const parsed = new URL(url, location.origin);
    return `${parsed.origin}${parsed.pathname}`;
  } catch {
    return url;
  }
}

function extractCardTitle(card) {
  if (!card) return '';
  const lines = (card.innerText || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  return lines[0] || '';
}

function extractCardAuthor(card) {
  if (!card) return '';
  const authorEl = card.querySelector('.author');
  if (authorEl) {
    const lines = (authorEl.innerText || '')
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .filter((line) => !/^关注$/i.test(line));
    return lines[0] || '';
  }
  const lines = (card.innerText || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  return lines[1] || '';
}

function extractCardCover(card) {
  if (!card) return null;
  const img = card.querySelector('img');
  return img?.src || null;
}

function extractCardUrl(card) {
  if (!card) return null;
  const link = card.querySelector('a[href*="/explore/"]');
  return link ? normalizeXiaohongshuUrl(link.href) : null;
}

function collectFeedItems() {
  return Array.from(document.querySelectorAll('section.note-item'))
    .map((card) => {
      const url = extractCardUrl(card);
      if (!url) return null;
      const text = (card.innerText || '').trim();
      return {
        title: extractCardTitle(card),
        author: extractCardAuthor(card),
        excerpt: text,
        cover: extractCardCover(card),
        url,
      };
    })
    .filter(Boolean);
}

function extractSearchKeyword() {
  const input = document.querySelector('#search-input');
  return (input?.value || '').trim();
}

function extractPostTitle() {
  const detailTitle = document.querySelector('#detail-title');
  const detailTitleText = (detailTitle?.innerText || '').trim();
  if (detailTitleText) return detailTitleText;
  const titleFromMeta = document.title.replace(/\s*-\s*小红书\s*$/, '').trim();
  const desc = document.querySelector('#detail-desc');
  const descText = (desc?.innerText || '').trim();
  if (!descText) return titleFromMeta;
  const firstLine = descText.split('\n').map((line) => line.trim()).filter(Boolean)[0];
  return firstLine || titleFromMeta;
}

function extractPostAuthor() {
  const authorEl = document.querySelector('.author');
  if (authorEl) {
    const lines = (authorEl.innerText || '')
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .filter((line) => !/^关注$/i.test(line))
      .map((line) => line.replace(/关注$/i, '').trim())
      .filter(Boolean);
    return lines[0] || '';
  }
  return '';
}

function extractPostImages() {
  const images = Array.from(document.querySelectorAll('img'))
    .map((img) => img.currentSrc || img.src || '')
    .filter((src) => src && /^https?:/i.test(src))
    .filter((src) => /xhscdn\.com/i.test(src))
    .filter((src) => /\/notes?_pre_post/i.test(src))
    .filter((src) => !/\/comment\//i.test(src));
  return Array.from(new Set(images)).slice(0, 12);
}

function detectHasVideo() {
  return !!document.querySelector('video');
}

function extractPostVideos() {
  const videos = Array.from(document.querySelectorAll('video'))
    .map((video) => video.currentSrc || video.src || '')
    .filter((src) => src && /^https?:/i.test(src))
    .filter((src) => /xhscdn\.com/i.test(src));
  return Array.from(new Set(videos)).slice(0, 6);
}

function appendPostMedia(text, images, videos) {
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

function extractPostText(images, videos) {
  const title = extractPostTitle();
  const desc = document.querySelector('#detail-desc');
  const descText = (desc?.innerText || '').trim();
  let baseText = '';
  if (!title) {
    baseText = descText;
  } else if (!descText || descText === title) {
    baseText = title;
  } else {
    baseText = `${title}\n\n${descText}`;
  }
  return appendPostMedia(baseText, images, videos);
}

const xiaohongshuAdapter = {
  id: 'xiaohongshu',
  match() {
    return isXiaohongshuHost();
  },
  getPageType() {
    return getXiaohongshuPageType();
  },
  capabilities() {
    return {
      read: ['read_post', 'read_home', 'search'],
      act: [],
    };
  },
  collect(baseSnapshot) {
    const pageType = getXiaohongshuPageType();
    const noteItems = collectFeedItems();
    const detailDesc = document.querySelector('#detail-desc');
    const postImages = pageType === 'post' ? extractPostImages() : [];
    const postVideos = pageType === 'post' ? extractPostVideos() : [];
    const hasVideo = pageType === 'post' ? detectHasVideo() : false;
    const ready = !!(
      document.readyState === 'complete' && (
        (pageType === 'post' && ((detailDesc && (detailDesc.innerText || '').trim().length > 0) || postImages.length > 0 || hasVideo)) ||
        ((pageType === 'home' || pageType === 'search') && noteItems.length > 0) ||
        (pageType === 'other' && (document.body?.innerText || '').trim().length > 100)
      )
    );

    return {
      site: 'xiaohongshu',
      page: baseSnapshot.page,
      signals: {
        ...baseSnapshot.signals,
        pageType,
        isXiaohongshu: true,
        ready,
        noteItemCount: noteItems.length,
        searchKeyword: pageType === 'search' ? extractSearchKeyword() : null,
        detailDescFound: !!detailDesc,
        hasVideo,
      },
      content: {
        items: noteItems,
        post: pageType === 'post' ? {
          title: extractPostTitle(),
          author: extractPostAuthor(),
          text: extractPostText(postImages, postVideos),
          images: postImages,
          videos: postVideos,
          url: normalizeXiaohongshuUrl(location.href),
        } : null,
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
    if (kind === 'read_post') {
      return {
        ok: true,
        mode: 'semantic',
        kind,
        page: snap.page,
        signals: snap.signals,
        content: snap.content.post || {},
      };
    }
    if (kind === 'read_home') {
      return {
        ok: true,
        mode: 'semantic',
        kind,
        page: snap.page,
        signals: snap.signals,
        content: {
          items: snap.content.items || [],
        },
      };
    }
    if (kind === 'search') {
      return {
        ok: true,
        mode: 'semantic',
        kind,
        page: snap.page,
        signals: snap.signals,
        content: {
          keyword: snap.signals.searchKeyword,
          items: snap.content.items || [],
        },
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
      error: 'No actions implemented for xiaohongshu',
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
window.BrowserBridgeAdapters.push(xiaohongshuAdapter);
