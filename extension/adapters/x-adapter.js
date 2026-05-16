// X (Twitter) Adapter for Browser Bridge

async function expandXLongPost() {
  const showMore = Array.from(document.querySelectorAll('div[role="button"]'))
    .find(el => /显示更多|Show more/i.test(el.innerText));
  if (showMore) {
    showMore.scrollIntoView({ behavior: 'smooth', block: 'center' });
    await new Promise(r => setTimeout(r, 800));
    showMore.click();
    return true;
  }
  return false;
}

function extractStatusId(url) {
  try {
    const parsed = new URL(url, location.origin);
    const parts = parsed.pathname.split('/').filter(Boolean);
    const index = parts.indexOf('status');
    if (index >= 0 && parts[index + 1]) return parts[index + 1];
  } catch {}
  return null;
}

function findArticleByStatusUrl(url) {
  const statusId = extractStatusId(url);
  if (!statusId) return null;
  const articles = Array.from(document.querySelectorAll('article[role="article"]'));
  return articles.find((article) => {
    return Array.from(article.querySelectorAll('a[href*="/status/"]')).some((link) => extractStatusId(link.href) === statusId);
  }) || null;
}

function findRemoveBookmarkControl(article) {
  if (!article) return null;
  const direct = article.querySelector('[data-testid="removeBookmark"]');
  if (direct) return direct;
  const controls = Array.from(article.querySelectorAll('button,[role="button"]'));
  return controls.find((el) => {
    const text = [
      el.getAttribute('aria-label') || '',
      el.getAttribute('data-testid') || '',
      el.getAttribute('title') || '',
      el.innerText || '',
    ].join(' ').trim();
    return /(移除书签|取消书签|remove bookmark|bookmarked)/i.test(text);
  }) || null;
}

function findAddBookmarkControl(article) {
  if (!article) return null;
  const direct = article.querySelector('[data-testid="bookmark"]');
  if (direct) return direct;
  const controls = Array.from(article.querySelectorAll('button,[role="button"]'));
  return controls.find((el) => {
    const text = [
      el.getAttribute('aria-label') || '',
      el.getAttribute('data-testid') || '',
      el.getAttribute('title') || '',
      el.innerText || '',
    ].join(' ').trim();
    return /(添加书签|加入书签|bookmark post|bookmark)/i.test(text) && !/(移除书签|取消书签|remove bookmark|bookmarked)/i.test(text);
  }) || null;
}

function extractProfileHandle(url = location.href) {
  try {
    const parsed = new URL(url, location.origin);
    const parts = parsed.pathname.split('/').filter(Boolean);
    if (parts.length !== 1) return null;
    const handle = parts[0];
    if (/^(home|search|explore|notifications|messages|i|compose|settings)$/i.test(handle)) return null;
    return handle;
  } catch {}
  return null;
}

function parseXMetricValue(raw) {
  if (raw === null || raw === undefined) return null;
  const text = String(raw).replace(/,/g, '').trim();
  const match = text.match(/([\d.]+)\s*([KMBkmb万亿]?)/);
  if (!match) return null;
  let value = Number(match[1]);
  if (!Number.isFinite(value)) return null;
  const unit = match[2];
  if (unit === 'K' || unit === 'k') value *= 1000;
  if (unit === 'M' || unit === 'm') value *= 1000000;
  if (unit === 'B' || unit === 'b') value *= 1000000000;
  if (unit === '万') value *= 10000;
  if (unit === '亿') value *= 100000000;
  return Math.round(value);
}

function extractXMetricNearLabel(labels) {
  const text = document.body?.innerText || '';
  for (const label of labels) {
    const pattern = new RegExp(`([\\d.,万亿KMBkmb]+)\\s*${label}`, 'i');
    const match = text.match(pattern);
    if (match) return parseXMetricValue(match[1]);
  }
  return null;
}

function extractXProfileMetrics() {
  const handle = extractProfileHandle();
  const userNameText = (document.querySelector('[data-testid="UserName"]')?.innerText || '').trim();
  const lines = userNameText.split('\n').map((line) => line.trim()).filter(Boolean);
  const displayName = lines.find((line) => !line.startsWith('@')) || document.title.split('/')[0].trim() || null;
  const bio = (document.querySelector('[data-testid="UserDescription"]')?.innerText || '').trim() || null;
  const followControl = findProfileFollowControl();
  return {
    handle: handle ? `@${handle}` : null,
    displayName,
    bio,
    metrics: {
      followers: extractXMetricNearLabel(['Followers', '粉丝']),
      following: extractXMetricNearLabel(['Following', '正在关注', '关注']),
      postsCount: extractXMetricNearLabel(['posts', 'Posts', '帖子']),
    },
    relationship: {
      followState: followControl ? followControl.state : null,
    },
    rawPayload: {
      profileHandle: handle,
    },
  };
}

function getFollowState(control) {
  if (!control) return null;
  const text = [
    control.getAttribute('aria-label') || '',
    control.getAttribute('data-testid') || '',
    control.getAttribute('title') || '',
    control.innerText || '',
  ].join(' ').trim();
  if (/(正在关注|已关注|following|following @|unfollow)/i.test(text)) return 'following';
  if (/(关注|follow)/i.test(text) && !/(正在关注|已关注|following)/i.test(text)) return 'not_following';
  return null;
}

function isElementVisible(el) {
  if (!el) return false;
  const rect = el.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

function findProfileFollowControl() {
  const main = document.querySelector('main') || document.body;
  const controls = Array.from(main.querySelectorAll('button,[role="button"]'))
    .filter((el) => isElementVisible(el))
    .filter((el) => !el.closest('article[role="article"]'))
    .map((el) => ({ el, state: getFollowState(el) }))
    .filter((item) => !!item.state);
  const anchor = document.querySelector('[data-testid="UserName"]');
  const anchorTop = anchor ? anchor.getBoundingClientRect().top : null;
  const scoped = anchorTop === null
    ? controls
    : controls.filter((item) => {
        const top = item.el.getBoundingClientRect().top;
        return top >= anchorTop - 80 && top <= anchorTop + 420;
      });
  const candidates = scoped.length ? scoped : controls;
  candidates.sort((a, b) => a.el.getBoundingClientRect().top - b.el.getBoundingClientRect().top);
  return candidates[0] || null;
}

function findUnfollowConfirmControl() {
  const dialog = document.querySelector('[role="dialog"]') || document.body;
  const controls = Array.from(dialog.querySelectorAll('button,[role="button"]'));
  return controls.find((el) => {
    const text = [
      el.getAttribute('aria-label') || '',
      el.getAttribute('data-testid') || '',
      el.getAttribute('title') || '',
      el.innerText || '',
    ].join(' ').trim();
    return /(取消关注|unfollow)/i.test(text);
  }) || null;
}

function extractRichText(container) {
  if (!container) return '';
  
  const fragments = [];
  const standaloneNoiseRegex = /^(主页|探索|通知|聊天|Grok|书签|更多|发帖|文章|对话|查看新帖子|订阅|分享|Home|Explore|Notifications|Messages|Bookmarks|More|Post|Articles|Subscribe|Share|什么是新鲜事|What’s happening|搜索|Search|要查看键盘快捷键，按下问号|键盘快捷键)$/i;

  let currentLine = '';

  const flushLine = () => {
    let trimmed = currentLine.trim();
    if (trimmed) {
      if (trimmed.length < 30 && standaloneNoiseRegex.test(trimmed)) {
        // noise, ignore
      } else if (trimmed.length < 15 && /^[\d\,\.]+([KMBkmb万亿]?)$/.test(trimmed)) {
        // metric noise, ignore
      } else if (trimmed.length < 20 && /^(查看|显示)\s*(更多|回复|相关|此对话|Show more)/i.test(trimmed)) {
        // action noise, ignore
      } else {
        fragments.push(trimmed);
      }
    }
    currentLine = '';
  };

  const walk = (node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      currentLine += node.nodeValue;
      return;
    }

    if (node.nodeType === Node.ELEMENT_NODE) {
      const tagName = node.tagName.toUpperCase();
      if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'NAV', 'HEADER', 'SVG', 'PATH'].includes(tagName)) return;

      const blockTags = ['DIV', 'P', 'BR', 'ARTICLE', 'LI', 'UL', 'OL', 'SECTION', 'H1', 'H2', 'H3'];
      if (blockTags.includes(tagName)) {
        flushLine();
      }

      if (tagName === 'IMG') {
        const src = node.src || '';
        const alt = node.alt || '';
        
        // Filter out UI icons, avatars, and hashflags
        if (!src.includes('profile_images') && !src.includes('semantic_core') && !src.includes('hashflags') && !src.includes('.svg')) {
          if (src.includes('emoji')) {
            currentLine += alt; // handle emojis inline
          } else {
            flushLine();
            let mediaText = `[Image: ${src}]`;
            if (alt && alt !== 'Image' && alt !== '图片' && alt !== '图像') {
              mediaText = `[Image: ${src} | Alt: ${alt}]`;
            }
            fragments.push(mediaText);
          }
        }
      } else if (tagName === 'VIDEO') {
        flushLine();
        const poster = node.getAttribute('poster');
        if (poster) {
           fragments.push(`[Video | Poster: ${poster}]`);
        } else {
           fragments.push(`[Video]`);
        }
      }

      // Recursively process child nodes
      for (const child of Array.from(node.childNodes)) {
        walk(child);
      }

      if (blockTags.includes(tagName)) {
        flushLine();
      }
    }
  };

  walk(container);
  flushLine();

  const filtered = [];
  for (let i = 0; i < fragments.length; i++) {
    if (i > 0 && fragments[i] === fragments[i-1]) continue;
    filtered.push(fragments[i]);
  }

  return filtered.join('\n\n').trim();
}

function cleanXPrimaryText(article, tweetText) {
  // Target X Long Articles (Notes) very specifically first based on the title container or rich text view
  const xArticleRoot = document.querySelector('[data-testid="twitter-article-title"]')?.closest('[role="article"]') 
                    || document.querySelector('[data-testid="twitterArticleRichTextView"]')?.closest('[role="article"]');
  
  if (xArticleRoot) {
    return extractRichText(xArticleRoot);
  }

  // Target regular tweets via the exact tweet text and its parent article
  const tweetRoot = document.querySelector('[data-testid="tweetText"]')?.closest('[role="article"]');
  if (tweetRoot) {
    return extractRichText(tweetRoot);
  }

  // Final fallback
  const fallbackContainer = article || document.querySelector('article[role="article"]') || document.body;
  return extractRichText(fallbackContainer);
}

function extractXTimeline() {
  const cells = Array.from(document.querySelectorAll('[data-testid="cellInnerDiv"]'));
  const directTweets = Array.from(document.querySelectorAll('[data-testid="tweet"]'));
  const articleTweets = Array.from(
    document.querySelectorAll('article[role="article"]')
  ).filter((el) => {
    return !!(el.querySelector('time') || el.querySelector('[data-testid="tweetText"]'));
  });

  const candidateMap = new Map();
  const addCandidate = (el) => {
    if (!el) return;
    const timeEl = el.querySelector('time');
    const urlEl = timeEl ? timeEl.closest('a') : null;
    const key = urlEl?.href || el.innerText?.slice(0, 80) || `anon-${candidateMap.size}`;
    if (!candidateMap.has(key)) candidateMap.set(key, el);
  };

  for (const cell of cells) addCandidate(cell.querySelector('[data-testid="tweet"]'));
  for (const tweetEl of directTweets) addCandidate(tweetEl);
  for (const articleEl of articleTweets) addCandidate(articleEl);

  const tweetNodes = Array.from(candidateMap.values());
  const timeline = [];
  for (const tweetEl of tweetNodes) {
    try {
      const timeEl = tweetEl.querySelector('time');
      const urlEl = timeEl ? timeEl.closest('a') : null;
      const url = urlEl ? urlEl.href : null;
      const authorEl = tweetEl.querySelector('[data-testid="User-Name"]');
      const authorInfo = authorEl ? authorEl.innerText.replace(/\n/g, ' ') : '';
      const publishedAt = timeEl?.getAttribute('datetime') || null;
      const publishedLabel = (timeEl?.innerText || '').trim() || null;

      let textContent = extractRichText(tweetEl);

      if (textContent.length > 0) {
         timeline.push({ authorInfo, publishedAt, publishedLabel, url, text: textContent });
      } else {
         timeline.push({ authorInfo, publishedAt, publishedLabel, url, text: "EMPTY_TEXT_FRAGMENTS" });
      }
    } catch (err) {
      console.warn('[Browser Bridge] Failed to parse a tweet in timeline', err);
      timeline.push({ error: err.toString(), message: err.message, stack: err.stack });
    }
  }
  return timeline;
}

function extractXTrendingItems() {
  const items = [];
  const cells = Array.from(document.querySelectorAll('[data-testid="trend"]'));
  for (const cell of cells) {
    const text = cell.textContent || '';
    if (/promoted|推广/i.test(text)) continue;
    const container = cell.querySelector(':scope > div') || cell;
    const parts = Array.from(container.children)
      .map((child) => (child.textContent || '').trim())
      .filter(Boolean);
    if (parts.length < 2) continue;
    const topic = parts[1];
    const category = (parts[0] || '').replace(/^\d+\s*/, '').replace(/^·\s*/, '').trim() || null;
    if (!topic) continue;
    items.push({
      rank: items.length + 1,
      topic,
      category,
    });
  }
  return items;
}

function detectXHomeFeedMode() {
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  if (!tabs.length) {
    return {
      mode: null,
      activeTabText: null,
      tabTexts: [],
    };
  }

  const selected = tabs.find((el) => el.getAttribute('aria-selected') === 'true') || null;
  const tabTexts = tabs.map((el) => (el.innerText || '').trim()).filter(Boolean);
  const activeText = (selected?.innerText || '').trim();
  const normalized = activeText.toLowerCase();

  let mode = null;
  if (activeText.includes('正在关注') || normalized.includes('following')) {
    mode = 'following';
  } else if (activeText.includes('为你推荐') || normalized.includes('for you')) {
    mode = 'for_you';
  }

  return {
    mode,
    activeTabText: activeText || null,
    tabTexts,
  };
}

async function switchXFeed(mode) {
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  const targetRegex = mode === 'following'
    ? /(正在关注|following)/i
    : /(为你推荐|for you)/i;
  const target = tabs.find((el) => targetRegex.test((el.innerText || '').trim()));
  if (!target) {
    return { ok: false, error: 'feed tab not found', mode };
  }

  const before = detectXHomeFeedMode();
  target.scrollIntoView({ behavior: 'smooth', block: 'center' });
  target.click();
  await new Promise((resolve) => setTimeout(resolve, 800));
  const after = detectXHomeFeedMode();
  return {
    ok: true,
    action: 'switch_feed',
    mode,
    changed: before.mode !== after.mode,
    before,
    after,
  };
}

const xAdapter = {
  id: 'x',
  match() {
    return location.hostname.includes('x.com') || location.hostname.includes('twitter.com');
  },
  getPageType() {
    if (/\/status\/\d+/.test(location.href)) return 'post';
    if (location.pathname === '/home') return 'home';
    if (location.pathname.startsWith('/search')) return 'search';
    if (location.pathname.startsWith('/explore')) return 'explore';
    if (location.pathname.startsWith('/i/bookmarks')) return 'bookmarks';
    if (/^\/[^/]+$/.test(location.pathname)) return 'profile';
    return 'other';
  },
  capabilities() {
    return {
      read: ['read_post', 'read_timeline', 'read_trending', 'list_bookmarks', 'read_profile_metrics', 'account_status'],
      act: ['expand_post', 'switch_feed', 'add_bookmark', 'remove_bookmark', 'follow_user', 'unfollow_user'],
    };
  },
  collect(baseSnapshot) {
    const article = document.querySelector('article[role="article"]');
    const tweetText = document.querySelector('[data-testid="tweetText"]');
    const loginMask = !!document.querySelector('[role="dialog"], [data-testid="sheetDialog"]');
    const sensitiveGate = /(敏感内容|sensitive content|age-restricted|成人内容|adult content)/i.test(document.body?.innerText || '');
    
    const isTweetDetail = /\/status\/\d+/.test(location.href);
    const isBookmarks = location.pathname.startsWith('/i/bookmarks');
    const isExplore = location.pathname.startsWith('/explore');
    const isTimeline = location.pathname === '/home' || location.pathname.startsWith('/search') || isExplore || isBookmarks;
    const feedModeInfo = isTimeline ? detectXHomeFeedMode() : { mode: null, activeTabText: null, tabTexts: [] };
    
    let primaryText = '';
    let timeline = [];
    let trends = [];
    
    if (isTweetDetail) {
      primaryText = cleanXPrimaryText(article, tweetText);
    } else if (isTimeline) {
      timeline = extractXTimeline();
      if (isExplore) trends = extractXTrendingItems();
    } else {
      primaryText = cleanXPrimaryText(article, tweetText);
      timeline = extractXTimeline();
    }

    const network = baseSnapshot.signals.network;
    const networkQuiet = !network || (network.pending === 0 && (network.quietMs === null || network.quietMs > 800));
    
    // CRITICAL GOTCHA: Guard against SPA "Fake Ready" states.
    // X.com renders the shell (sidebar/nav) instantly, which could trigger a primaryText > 20 chars
    // while the actual tweet is still fetching via GraphQL. We MUST force the extension to remain `ready: false` 
    // until the absolute core content container (either a tweet or a long article) explicitly appears in the DOM.
    const isXArticle = !!document.querySelector('[data-testid="twitter-article-title"]') || !!document.querySelector('[data-testid="twitterArticleRichTextView"]');
    const hasCoreContent = isXArticle || !!tweetText;

    const ready = !!(
      document.readyState === 'complete' &&
      (
        (isTweetDetail && hasCoreContent && primaryText.length > 20)
        || (isExplore && (trends.length > 0 || document.body.innerText.length > 500))
        || (isTimeline && timeline.length > 0)
        || (!isTweetDetail && !isTimeline && document.body.innerText.length > 100)
      ) &&
      !loginMask &&
      networkQuiet
    );
    
    return {
      site: 'x',
      page: baseSnapshot.page,
      signals: {
        ...baseSnapshot.signals,
        isX: true,
        isTweetDetail,
        isTimeline,
        isExplore,
        isBookmarks,
        feedMode: feedModeInfo.mode,
        activeFeedTabText: feedModeInfo.activeTabText,
        feedTabTexts: feedModeInfo.tabTexts,
        articleFound: !!article,
        tweetTextFound: !!tweetText,
        loginMask,
        sensitiveGate,
        networkQuiet,
        ready,
      },
      content: {
        primaryText: primaryText,
        timeline: timeline,
        trends,
      },
    };
  },
  async probeReady(context) {
    const snap = this.collect(context.baseSnapshot);
    return {
      ok: true,
      site: snap.site,
      page: snap.page,
      signals: {
        ...snap.signals,
        pageType: this.getPageType(),
      },
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
        content: {
          primaryText: snap.content.primaryText,
        },
      };
    }
    if (kind === 'read_timeline' || kind === 'list_bookmarks') {
      return {
        ok: true,
        mode: 'semantic',
        kind,
        page: snap.page,
        signals: snap.signals,
        content: {
          timeline: snap.content.timeline,
        },
      };
    }
    if (kind === 'read_trending') {
      return {
        ok: true,
        mode: 'semantic',
        kind,
        page: snap.page,
        signals: snap.signals,
        content: {
          url: location.href,
          items: snap.content.trends,
          rawPayload: {
            pageType: this.getPageType(),
            itemCount: snap.content.trends.length,
            source: 'x-trending-dom',
          },
        },
      };
    }
    if (kind === 'read_profile_metrics') {
      return {
        ok: true,
        mode: 'semantic',
        kind,
        page: snap.page,
        signals: snap.signals,
        content: {
          url: location.href,
          ...extractXProfileMetrics(),
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
    const snap = this.collect(context.baseSnapshot);
    if (kind === 'expand_post') {
      const changed = await expandXLongPost();
      return {
        ok: true,
        action: kind,
        changed,
        before: {
          primaryTextLength: (snap.content.primaryText || '').length,
        },
      };
    }
    if (kind === 'switch_feed') {
      return await switchXFeed(params.mode || 'for_you');
    }
    if (kind === 'add_bookmark') {
      const targetUrl = params.url || location.href;
      const targetStatusId = extractStatusId(targetUrl);
      const article = findArticleByStatusUrl(targetUrl)
        || ((targetStatusId && targetStatusId === extractStatusId(location.href))
          ? document.querySelector('article[role="article"]')
          : null);
      if (!article) {
        return {
          ok: false,
          action: kind,
          page: snap.page,
          error: 'bookmark article not found',
        };
      }
      const control = findAddBookmarkControl(article);
      if (!control) {
        return {
          ok: false,
          action: kind,
          page: snap.page,
          error: 'add bookmark control not found',
        };
      }
      const beforeText = extractRichText(article).slice(0, 500);
      const authorInfo = (article.querySelector('[data-testid="User-Name"]')?.innerText || '').replace(/\n/g, ' ');
      control.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await new Promise((resolve) => setTimeout(resolve, 500));
      control.click();
      await new Promise((resolve) => setTimeout(resolve, 1000));
      return {
        ok: true,
        action: kind,
        changed: true,
        before: {
          url: targetUrl,
          authorInfo,
          text: beforeText,
        },
      };
    }
    if (kind === 'remove_bookmark') {
      const targetUrl = params.url || '';
      const article = findArticleByStatusUrl(targetUrl);
      if (!article) {
        return {
          ok: false,
          action: kind,
          page: snap.page,
          error: 'bookmark article not found',
        };
      }
      const control = findRemoveBookmarkControl(article);
      if (!control) {
        return {
          ok: false,
          action: kind,
          page: snap.page,
          error: 'remove bookmark control not found',
        };
      }
      const beforeText = extractRichText(article).slice(0, 500);
      const authorInfo = (article.querySelector('[data-testid="User-Name"]')?.innerText || '').replace(/\n/g, ' ');
      control.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await new Promise((resolve) => setTimeout(resolve, 500));
      control.click();
      await new Promise((resolve) => setTimeout(resolve, 1000));
      return {
        ok: true,
        action: kind,
        changed: true,
        before: {
          url: targetUrl,
          authorInfo,
          text: beforeText,
        },
      };
    }
    if (kind === 'follow_user' || kind === 'unfollow_user') {
      const expectedHandle = (params.handle || '').replace(/^@/, '').trim();
      const currentHandle = extractProfileHandle(location.href);
      if (!currentHandle) {
        return {
          ok: false,
          action: kind,
          page: snap.page,
          error: 'follow actions only support profile page',
        };
      }
      if (expectedHandle && currentHandle.toLowerCase() !== expectedHandle.toLowerCase()) {
        return {
          ok: false,
          action: kind,
          page: snap.page,
          error: 'profile handle mismatch',
        };
      }
      const targetHandle = expectedHandle || currentHandle;
      const controlInfo = findProfileFollowControl();
      if (!controlInfo) {
        return {
          ok: false,
          action: kind,
          page: snap.page,
          error: 'follow control not found',
        };
      }
      const beforeState = controlInfo.state;
      if (kind === 'follow_user' && beforeState === 'following') {
        return {
          ok: true,
          action: kind,
          changed: false,
          before: { handle: targetHandle, state: beforeState },
        };
      }
      if (kind === 'unfollow_user' && beforeState === 'not_following') {
        return {
          ok: true,
          action: kind,
          changed: false,
          before: { handle: targetHandle, state: beforeState },
        };
      }

      controlInfo.el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await new Promise((resolve) => setTimeout(resolve, 500));
      controlInfo.el.click();

      if (kind === 'unfollow_user') {
        await new Promise((resolve) => setTimeout(resolve, 600));
        const confirm = findUnfollowConfirmControl();
        if (confirm) {
          confirm.click();
        }
      }

      await new Promise((resolve) => setTimeout(resolve, 1200));
      return {
        ok: true,
        action: kind,
        changed: true,
        before: {
          handle: targetHandle,
          state: beforeState,
        },
      };
    }
    return {
      ok: false,
      action: kind,
      page: snap.page,
      error: `Unsupported action kind: ${kind}`,
    };
  },
  async verify(kind, params, context, actionResult) {
    const snap = this.collect(context.baseSnapshot);
    if (kind === 'switch_feed') {
      const expectedMode = params.mode || 'for_you';
      return {
        ok: true,
        verified: snap.signals.feedMode === expectedMode,
        after: {
          feedMode: snap.signals.feedMode,
        },
        actionResult,
      };
    }
    if (kind === 'remove_bookmark') {
      const targetUrl = params.url || ((actionResult || {}).get('before') || {}).url || '';
      const afterArticle = findArticleByStatusUrl(targetUrl);
      return {
        ok: true,
        verified: !afterArticle || !findRemoveBookmarkControl(afterArticle),
        after: {
          url: targetUrl,
          stillVisible: !!afterArticle,
        },
        actionResult,
      };
    }
    if (kind === 'add_bookmark') {
      const targetUrl = params.url || ((actionResult || {}).get('before') || {}).url || location.href;
      const afterArticle = findArticleByStatusUrl(targetUrl) || document.querySelector('article[role="article"]');
      return {
        ok: true,
        verified: !!afterArticle && !!findRemoveBookmarkControl(afterArticle),
        after: {
          url: targetUrl,
          visible: !!afterArticle,
        },
        actionResult,
      };
    }
    if (kind === 'follow_user' || kind === 'unfollow_user') {
      const currentHandle = extractProfileHandle(location.href);
      const expectedHandle = (params.handle || currentHandle || '').replace(/^@/, '').trim();
      const controlInfo = findProfileFollowControl();
      const state = controlInfo ? controlInfo.state : null;
      const expectedState = kind === 'follow_user' ? 'following' : 'not_following';
      return {
        ok: true,
        verified: state === expectedState,
        after: {
          handle: expectedHandle || null,
          state,
        },
        actionResult,
      };
    }
    return {
      ok: true,
      verified: !!actionResult?.ok,
      actionResult,
    };
  }
};

// Auto-register to the global registry
window.BrowserBridgeAdapters = window.BrowserBridgeAdapters || [];
window.BrowserBridgeAdapters.push(xAdapter);
