(function registerDoubanAdapter() {
  const DOUBAN_ADAPTER_VERSION = 'douban-subject-v1-2026-07-01';
  const INTEREST_VALUES = new Set(['wish', 'do', 'collect']);
  const INTEREST_LABELS = {
    wish: '想看',
    do: '在看',
    collect: '看过',
  };

  function compactText(value) {
    return (value || '').replace(/\s+/g, ' ').trim();
  }

  function absoluteUrl(value, base = location.href) {
    if (!value) return null;
    try {
      return new URL(value, base).href;
    } catch {
      return value;
    }
  }

  function parseCount(value) {
    if (value === null || value === undefined) return null;
    const text = String(value).replace(/,/g, '').trim();
    if (!text) return null;
    const match = text.match(/([\d.]+)\s*([万亿kKmM]?)/);
    if (!match) return null;
    let number = Number(match[1]);
    if (!Number.isFinite(number)) return null;
    const unit = match[2];
    if (unit === '万') number *= 10000;
    if (unit === '亿') number *= 100000000;
    if (unit === 'k' || unit === 'K') number *= 1000;
    if (unit === 'm' || unit === 'M') number *= 1000000;
    return Math.round(number);
  }

  function getPageType() {
    const host = location.hostname.toLowerCase();
    const path = location.pathname;
    if (host === 'www.douban.com' && path.startsWith('/search')) return 'search';
    if (host === 'movie.douban.com' && /^\/subject\/\d+\/?/.test(path)) return 'post';
    if (/^\/people\//.test(path) || /^\/group\//.test(path)) return 'profile';
    return 'unknown';
  }

  function subjectIdFromUrl(url = location.href) {
    try {
      const parsed = new URL(url, location.href);
      const match = parsed.pathname.match(/\/subject\/(\d+)/);
      return match ? match[1] : null;
    } catch {
      return null;
    }
  }

  function subjectRefFromUrl(url) {
    if (!url) return null;
    try {
      const parsed = new URL(url, location.href);
      const direct = parsed.pathname.match(/\/subject\/(\d+)/);
      if (parsed.hostname === 'movie.douban.com' && direct) {
        return {
          id: direct[1],
          url: `https://movie.douban.com/subject/${direct[1]}/`,
        };
      }
      if (parsed.hostname === 'www.douban.com' && parsed.pathname.startsWith('/doubanapp/dispatch')) {
        const uri = parsed.searchParams.get('uri') || '';
        const dispatched = uri.match(/^\/(?:movie|tv)\/(\d+)/);
        if (dispatched) {
          return {
            id: dispatched[1],
            url: `https://movie.douban.com/subject/${dispatched[1]}/`,
          };
        }
      }
    } catch {}
    return null;
  }

  function parseLdJson() {
    const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
    for (const script of scripts) {
      try {
        const raw = (script.textContent || '').trim();
        if (!raw) continue;
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          const item = parsed.find((entry) => entry && (entry.name || entry['@type']));
          if (item) return item;
        }
        if (parsed && typeof parsed === 'object') return parsed;
      } catch {}
    }
    return {};
  }

  function normalizePerson(value) {
    if (!value) return null;
    if (typeof value === 'string') return { name: compactText(value), url: null };
    const name = compactText(value.name || value.displayName || '');
    if (!name) return null;
    return {
      name,
      url: absoluteUrl(value.url || value.sameAs || null),
    };
  }

  function normalizePeople(value) {
    const values = Array.isArray(value) ? value : (value ? [value] : []);
    return values.map(normalizePerson).filter(Boolean);
  }

  function infoText() {
    const info = document.querySelector('#info');
    return info ? (info.innerText || '') : '';
  }

  function extractInfoLine(label) {
    const text = infoText();
    const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const match = text.match(new RegExp(`${escaped}:\\s*([^\\n]+)`));
    return match ? compactText(match[1]) : null;
  }

  function splitSlashList(value) {
    if (!value) return [];
    return value.split('/').map((item) => compactText(item)).filter(Boolean);
  }

  function parseYear(title) {
    const match = (title || document.title || '').match(/\((\d{4})\)/);
    return match ? Number(match[1]) : null;
  }

  function titleText() {
    const h1 = document.querySelector('#content h1') || document.querySelector('h1');
    return compactText(h1?.innerText || document.title || '').replace(/\s*\(\d{4}\)\s*$/, '');
  }

  function extractSummary(ld) {
    const visibleSummary = compactText(
      document.querySelector('[property="v:summary"]')?.innerText
      || document.querySelector('#link-report-intra')?.innerText
      || ''
    );
    return visibleSummary || compactText(ld.description || '');
  }

  function extractCover(ld) {
    const image = ld.image || document.querySelector('meta[property="og:image"]')?.getAttribute('content');
    if (typeof image === 'string') return absoluteUrl(image);
    if (Array.isArray(image) && image.length) return absoluteUrl(image[0]);
    return null;
  }

  function parseRating(ld) {
    const aggregate = ld.aggregateRating || {};
    const score = parseFloat(aggregate.ratingValue || document.querySelector('[property="v:average"]')?.innerText || '');
    const count = parseCount(aggregate.ratingCount || aggregate.reviewCount || document.querySelector('[property="v:votes"]')?.innerText);
    return {
      score: Number.isFinite(score) ? score : null,
      ratingCount: count,
      best: parseFloat(aggregate.bestRating || 10) || 10,
      worst: parseFloat(aggregate.worstRating || 2) || 2,
      starWeights: [],
    };
  }

  function extractInterestStats() {
    const text = compactText(document.body?.innerText || '');
    const labels = {
      wish: ['想看'],
      do: ['在看'],
      collect: ['看过'],
    };
    const result = { wish: null, do: null, collect: null };
    for (const [key, names] of Object.entries(labels)) {
      for (const name of names) {
        const patterns = [
          new RegExp(`(\\d[\\d,]*(?:\\.\\d+)?\\s*[万亿kKmM]?)\\s*人\\s*${name}`),
          new RegExp(`${name}\\s*(\\d[\\d,]*(?:\\.\\d+)?\\s*[万亿kKmM]?)`),
        ];
        for (const pattern of patterns) {
          const match = text.match(pattern);
          if (match) {
            result[key] = parseCount(match[1]);
            break;
          }
        }
        if (result[key] !== null) break;
      }
    }
    return result;
  }

  function findInterestControls() {
    const controls = {};
    const candidates = Array.from(document.querySelectorAll('a, button, input[type="button"], input[type="submit"]'));
    for (const el of candidates) {
      const href = el.getAttribute('href') || '';
      const name = el.getAttribute('name') || '';
      const value = el.getAttribute('value') || '';
      const text = compactText(`${el.innerText || ''} ${el.getAttribute('title') || ''} ${el.getAttribute('aria-label') || ''} ${value}`);
      const combined = `${href} ${name} ${text}`;
      const inInterestSection = Boolean(el.closest('#interest_sect_level'));
      for (const interest of INTEREST_VALUES) {
        if (controls[interest]) continue;
        const exactControl = (
          combined.includes(`interest=${interest}`)
          || combined.includes(`pbtn-${subjectIdFromUrl() || ''}-${interest}`)
        );
        const labelControl = inInterestSection && new RegExp(`^${INTEREST_LABELS[interest]}$`).test(text);
        if (
          exactControl
          || labelControl
        ) {
          controls[interest] = el;
        }
      }
    }
    return controls;
  }

  function detectViewerInterest() {
    const interestSectionText = compactText(document.querySelector('#interest_sect_level')?.innerText || '');
    for (const interest of INTEREST_VALUES) {
      if (new RegExp(`我${INTEREST_LABELS[interest]}|已${INTEREST_LABELS[interest]}|取消${INTEREST_LABELS[interest]}`).test(interestSectionText)) {
        return { value: interest, label: INTEREST_LABELS[interest], detected: true };
      }
    }
    const controls = findInterestControls();
    for (const interest of INTEREST_VALUES) {
      const el = controls[interest];
      if (!el) continue;
      const classes = el.className || '';
      const ariaPressed = el.getAttribute('aria-pressed');
      const parentText = compactText(el.parentElement?.innerText || '');
      if (
        ariaPressed === 'true'
        || /selected|active|done|on|interest/.test(String(classes))
        || new RegExp(`已${INTEREST_LABELS[interest]}|我${INTEREST_LABELS[interest]}|取消${INTEREST_LABELS[interest]}`).test(parentText)
      ) {
        return { value: interest, label: INTEREST_LABELS[interest], detected: true };
      }
    }
    if (Object.keys(controls).length > 0) {
      return { value: null, label: null, detected: true };
    }
    return { value: null, label: null, detected: false };
  }

  function extractRatingFromClass(el) {
    const classText = el?.className || '';
    const match = String(classText).match(/allstar(\d+)/);
    if (!match) return { rating: null, ratingLabel: null };
    return {
      rating: Math.round(Number(match[1]) / 10),
      ratingLabel: el.getAttribute('title') || null,
    };
  }

  function extractComments(limit, root = document, baseUrl = location.href) {
    const items = [];
    const nodes = Array.from(root.querySelectorAll('.comment-item, [class*="comment-item"]'));
    const max = Math.max(0, Math.min(Number(limit ?? 20) || 0, 100));
    if (max === 0) return items;
    for (const node of nodes) {
      if (items.length >= max) break;
      const authorLink = node.querySelector('.comment-info a[href*="/people/"], a[href*="/people/"]');
      const ratingEl = node.querySelector('[class*="allstar"]');
      const voteText = node.querySelector('.votes, .vote-count')?.innerText || '';
      const commentText = compactText(
        node.querySelector('.short, .comment-content, [class*="comment-content"]')?.innerText
        || node.querySelector('p')?.innerText
        || ''
      );
      if (!commentText) continue;
      const timeEl = node.querySelector('.comment-time, [class*="time"]');
      const statusText = compactText(node.querySelector('.comment-info .rating')?.previousSibling?.textContent || '');
      const infoTextValue = compactText(node.querySelector('.comment-info')?.innerText || '');
      const statusMatch = infoTextValue.match(/(想看|在看|看过)/);
      const locationMatch = infoTextValue.match(/\s([^\s]+)$/);
      const rating = extractRatingFromClass(ratingEl);
      const statusLabel = statusMatch ? statusMatch[1] : null;
      const status = statusLabel === '想看' ? 'wish' : statusLabel === '在看' ? 'do' : statusLabel === '看过' ? 'collect' : null;
      items.push({
        id: node.getAttribute('data-cid') || node.id || null,
        authorName: compactText(authorLink?.innerText || ''),
        author: {
          displayName: compactText(authorLink?.innerText || '') || null,
          profileUrl: absoluteUrl(authorLink?.getAttribute('href') || null, baseUrl),
        },
        time: compactText(timeEl?.getAttribute('title') || timeEl?.innerText || ''),
        text: commentText,
        media: [],
        metrics: {
          likes: parseCount(voteText),
          comments: null,
        },
        platformMetrics: {
          status,
          statusLabel,
          rating: rating.rating,
          ratingLabel: rating.ratingLabel,
          location: locationMatch ? locationMatch[1] : null,
        },
        debug: statusText ? { statusText } : undefined,
      });
    }
    return items.map((item) => {
      if (!item.debug) return item;
      const copy = { ...item };
      delete copy.debug;
      return copy;
    });
  }

  async function fetchMoreComments(subjectId, currentItems, limit) {
    const max = Math.max(0, Math.min(Number(limit ?? 20) || 0, 100));
    if (!subjectId || max === 0 || currentItems.length >= max) return currentItems;
    const seen = new Set(currentItems.map((item) => item.id || `${item.authorName}\n${item.time}\n${item.text}`));
    const url = `https://movie.douban.com/subject/${subjectId}/comments?limit=${max}&status=P&sort=new_score`;
    try {
      const response = await fetch(url, { credentials: 'include' });
      if (!response.ok) return currentItems;
      const html = await response.text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const fetched = extractComments(max, doc, url);
      const merged = currentItems.slice();
      for (const item of fetched) {
        const key = item.id || `${item.authorName}\n${item.time}\n${item.text}`;
        if (seen.has(key)) continue;
        seen.add(key);
        merged.push(item);
        if (merged.length >= max) break;
      }
      return merged;
    } catch {
      return currentItems;
    }
  }

  function commentsTotal() {
    const text = compactText(document.body?.innerText || '');
    const match = text.match(/全部\s*(\d[\d,]*)\s*条|(\d[\d,]*)\s*条短评/);
    return parseCount(match?.[1] || match?.[2] || null);
  }

  function extractSubject(params = {}) {
    const ld = parseLdJson();
    const title = compactText(ld.name || titleText());
    const originalTitle = extractInfoLine('原名') || extractInfoLine('又名') || null;
    const releaseLabel = extractInfoLine('首播') || extractInfoLine('上映日期') || compactText(ld.datePublished || '');
    const releaseDate = compactText(ld.datePublished || '') || (releaseLabel || '').match(/\d{4}-\d{2}-\d{2}/)?.[0] || null;
    const genres = splitSlashList(extractInfoLine('类型') || '').length
      ? splitSlashList(extractInfoLine('类型') || '')
      : (Array.isArray(ld.genre) ? ld.genre : splitSlashList(ld.genre || ''));
    const subject = {
      id: subjectIdFromUrl(),
      title,
      originalTitle,
      year: parseYear(document.querySelector('#content h1')?.innerText || document.title),
      category: /集数|单集片长|首播/.test(infoText()) ? 'tv_series' : 'movie',
      cover: extractCover(ld),
      summary: extractSummary(ld),
      directors: normalizePeople(ld.director || splitSlashList(extractInfoLine('导演') || '')),
      writers: normalizePeople(ld.author || ld.creator || splitSlashList(extractInfoLine('编剧') || '')),
      actors: normalizePeople(ld.actor || splitSlashList(extractInfoLine('主演') || '')),
      genres,
      countries: splitSlashList(extractInfoLine('制片国家/地区') || ''),
      languages: splitSlashList(extractInfoLine('语言') || ''),
      releaseDate,
      releaseLabel: releaseLabel || null,
      episodeCount: parseCount(extractInfoLine('集数')),
      aka: splitSlashList(extractInfoLine('又名') || ''),
      imdb: extractInfoLine('IMDb') || null,
    };
    const rating = parseRating(ld);
    const interestStats = extractInterestStats();
    const commentLimit = Math.max(0, Math.min(Number(params.commentLimit ?? 20) || 0, 100));
    const comments = extractComments(commentLimit);
    const total = commentsTotal();
    return {
      url: location.href,
      externalPostId: subject.id,
      platformType: 'douban_subject',
      subject,
      rating,
      interestStats,
      viewerInterest: detectViewerInterest(),
      metrics: {
        comments: total,
        favorites: null,
      },
      comments,
      commentsTotal: total,
      commentsHasMore: total !== null ? comments.length < total : null,
      rawPayload: {
        adapterVersion: DOUBAN_ADAPTER_VERSION,
        pageType: getPageType(),
        commentCount: comments.length,
      },
    };
  }

  async function extractSubjectWithFetchedComments(params = {}) {
    const content = extractSubject(params);
    const commentLimit = Math.max(0, Math.min(Number(params.commentLimit ?? 20) || 0, 100));
    if (commentLimit > content.comments.length && content.subject?.id) {
      content.comments = await fetchMoreComments(content.subject.id, content.comments, commentLimit);
      content.commentsHasMore = content.commentsTotal !== null ? content.comments.length < content.commentsTotal : null;
      content.rawPayload = {
        ...content.rawPayload,
        commentCount: content.comments.length,
        commentsFetchAttempted: true,
      };
    }
    return content;
  }

  function extractSearchItems(params = {}) {
    const count = Math.max(1, Math.min(Number(params.count || params.limit || 10) || 10, 50));
    const items = [];
    const filteredItems = [];
    const links = Array.from(document.querySelectorAll('a[href*="movie.douban.com/subject/"], a[href*="/doubanapp/dispatch"], .result a[href]'));
    const seen = new Set();
    const seenSubjectIds = new Set();
    for (const link of links) {
      const url = absoluteUrl(link.getAttribute('href'));
      if (!url || seen.has(url)) continue;
      seen.add(url);
      let parsed;
      try {
        parsed = new URL(url);
      } catch {
        continue;
      }
      const subjectRef = subjectRefFromUrl(url);
      const id = subjectRef?.id || subjectIdFromUrl(url);
      const row = link.closest('.result, .result-list, .item') || link.parentElement;
      const title = compactText(link.innerText || row?.querySelector('.title')?.innerText || '');
      if (!subjectRef && (parsed.hostname !== 'movie.douban.com' || !id)) {
        filteredItems.push({ reason: 'non_subject_result', url, title });
        continue;
      }
      if (!title) continue;
      if (seenSubjectIds.has(id)) continue;
      seenSubjectIds.add(id);
      const text = compactText(row?.innerText || '');
      const image = row?.querySelector('img')?.src || null;
      const ratingMatch = text.match(/评分[:：]?\s*([\d.]+)/);
      items.push({
        id,
        url: subjectRef?.url || url,
        title,
        subtitle: text.replace(title, '').slice(0, 180),
        type: 'subject',
        cover: absoluteUrl(image),
        rating: ratingMatch ? Number(ratingMatch[1]) : null,
        summary: text.slice(0, 240),
      });
      if (items.length >= count) break;
    }
    return {
      items,
      filteredItems,
    };
  }

  function blockingNotice() {
    const text = compactText(document.body?.innerText || '');
    return /验证码|安全验证|访问过于频繁|请先登录|登录后|abnormal|verify/i.test(text);
  }

  function collect(baseSnapshot) {
    const pageType = getPageType();
    const notice = blockingNotice();
    const content = pageType === 'post' ? extractSubject({ commentLimit: 20 }) : {};
    return {
      ...baseSnapshot,
      site: 'douban',
      signals: {
        ...baseSnapshot.signals,
        ready: Boolean(
          document.readyState === 'complete'
          && (document.querySelector('#content h1') || document.querySelector('#info') || document.querySelector('.result') || notice)
        ),
        pageType,
        needsHumanAttention: notice,
      },
      content: {
        ...baseSnapshot.content,
        ...content,
      },
    };
  }

  async function setInterest(params, context) {
    const interest = params.interest;
    if (!INTEREST_VALUES.has(interest)) {
      return { ok: false, action: 'set_interest', error: 'invalid_interest' };
    }
    const before = detectViewerInterest();
    const notice = blockingNotice();
    if (notice) {
      return { ok: false, action: 'set_interest', before, error: 'needs_human_attention' };
    }
    if (!before.detected) {
      return {
        ok: false,
        action: 'set_interest',
        before,
        error: 'viewerInterest undetected',
        debug: {
          reason: 'viewerInterest undetected',
        },
      };
    }
    if (before.value === interest) {
      return {
        ok: true,
        action: 'set_interest',
        changed: false,
        before: {
          interest: before.value,
          label: before.label,
          detected: before.detected,
          url: params.url || location.href,
        },
        after: {
          interest: before.value,
          label: before.label,
          detected: before.detected,
          url: params.url || location.href,
        },
        page: context?.baseSnapshot?.page,
      };
    }
    const controls = findInterestControls();
    const control = controls[interest];
    if (!control) {
      return { ok: false, action: 'set_interest', before, error: 'interest control not found' };
    }
    control.scrollIntoView({ behavior: 'smooth', block: 'center' });
    await new Promise((resolve) => setTimeout(resolve, 500));
    control.click();
    await new Promise((resolve) => setTimeout(resolve, 800));
    const form = document.querySelector(`form.a_interest_form input[name="interest"][value="${interest}"]`)?.closest('form');
    if (form) {
      const submit = form.querySelector('input[type="submit"][name="save"], input[type="submit"], button[type="submit"]');
      if (!submit) {
        return { ok: false, action: 'set_interest', before, error: 'interest form submit not found' };
      }
      submit.click();
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
    const after = detectViewerInterest();
    const updated = after.value === interest;
    return {
      ok: updated,
      action: 'set_interest',
      changed: before.value !== after.value,
      before: {
        interest: before.value,
        label: before.label,
        detected: before.detected,
        url: params.url || location.href,
      },
      after: {
        interest: after.value,
        label: after.label,
        detected: after.detected,
        url: params.url || location.href,
      },
      page: context?.baseSnapshot?.page,
      error: updated ? null : 'interest state not updated',
    };
  }

  const doubanAdapter = {
    id: 'douban',
    site: 'douban',
    match() {
      const host = location.hostname.toLowerCase();
      return host === 'douban.com' || host.endsWith('.douban.com');
    },
    capabilities() {
      return {
        site: 'douban',
        read: ['read_post', 'read_profile_metrics', 'search', 'account_status'],
        action: ['set_interest'],
        workflow: ['read_post', 'read_profile_metrics', 'search', 'set_interest', 'account_status'],
      };
    },
    getPageType,
    collect,
    async probeReady(context) {
      const snap = collect(context.baseSnapshot);
      return {
        ok: true,
        site: 'douban',
        page: snap.page,
        pageType: getPageType(),
        signals: snap.signals,
        content: snap.content,
      };
    },
    async read(kind, params, context) {
      const snap = collect(context.baseSnapshot);
      if (kind === 'read_post') {
        return {
          ok: getPageType() === 'post',
          mode: 'semantic',
          kind,
          pageType: getPageType(),
          page: snap.page,
          signals: snap.signals,
          content: await extractSubjectWithFetchedComments(params),
          error: getPageType() === 'post' ? undefined : 'unsupported douban page type',
        };
      }
      if (kind === 'search') {
        const results = extractSearchItems(params);
        return {
          ok: true,
          mode: 'semantic',
          kind,
          pageType: getPageType(),
          page: snap.page,
          signals: snap.signals,
          content: {
            url: location.href,
            keyword: params.keyword || new URLSearchParams(location.search).get('q') || '',
            items: results.items,
            filteredItems: results.filteredItems,
            rawPayload: {
              adapterVersion: DOUBAN_ADAPTER_VERSION,
              itemCount: results.items.length,
              filteredCount: results.filteredItems.length,
            },
          },
        };
      }
      if (kind === 'read_profile_metrics') {
        return {
          ok: true,
          mode: 'semantic',
          kind,
          pageType: getPageType(),
          page: snap.page,
          signals: snap.signals,
          content: {
            url: location.href,
            viewerInterest: detectViewerInterest(),
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
    async act(kind, params, context) {
      if (kind === 'set_interest') return setInterest(params, context);
      return { ok: false, action: kind, error: `Unsupported action kind: ${kind}` };
    },
    async verify(kind, params, context, actionResult) {
      if (kind !== 'set_interest') {
        return { ok: false, verified: false, error: `Unsupported verify kind: ${kind}`, actionResult };
      }
      const after = detectViewerInterest();
      return {
        ok: true,
        verified: after.value === params.interest,
        after: {
          interest: after.value,
          label: after.label,
          detected: after.detected,
          url: params.url || location.href,
        },
        actionResult,
      };
    },
  };

  window.BrowserBridgeAdapters = window.BrowserBridgeAdapters || [];
  window.BrowserBridgeAdapters.push(doubanAdapter);
})();
