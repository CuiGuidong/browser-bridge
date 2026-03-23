// Site adapter registry for Browser Bridge Extension

function getRequestProbeState() {
  try {
    const attr = document.documentElement?.getAttribute('data-browser-bridge-probe');
    if (!attr) return null;
    const state = JSON.parse(attr);
    if (state.lastRequestFinishedAt) {
      state.quietMs = Date.now() - state.lastRequestFinishedAt;
    }
    return state;
  } catch {
    return null;
  }
}

function collectGenericSnapshot() {
  const text = (document.body?.innerText || '').trim();
  const network = getRequestProbeState();
  return {
    site: location.hostname,
    page: {
      url: location.href,
      title: document.title || '',
      hostname: location.hostname,
    },
    signals: {
      readyState: document.readyState,
      bodyTextLength: text.length,
      network,
      ready: text.length > 120 && document.readyState === 'complete',
    },
    content: {
      primaryText: text,
    },
  };
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
  ).filter((el) => !!(el.querySelector('time') || el.querySelector('[data-testid="tweetText"]')));

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
      }
    } catch (err) {
      console.warn('[Browser Bridge] Failed to parse a tweet in timeline', err);
    }
  }
  return timeline;
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

const xAdapter = {
  id: 'x',
  match() {
    return location.hostname.includes('x.com') || location.hostname.includes('twitter.com');
  },
  collect() {
    const base = collectGenericSnapshot();
    
    const article = document.querySelector('article[role="article"]');
    const tweetText = document.querySelector('[data-testid="tweetText"]');
    const loginMask = !!document.querySelector('[role="dialog"], [data-testid="sheetDialog"]');
    const sensitiveGate = /(敏感内容|sensitive content|age-restricted|成人内容|adult content)/i.test(document.body?.innerText || '');
    
    const isTweetDetail = /\/status\/\d+/.test(location.href);
    const isTimeline = location.pathname === '/home' || location.pathname.startsWith('/search') || location.pathname.startsWith('/explore');
    const feedModeInfo = isTimeline ? detectXHomeFeedMode() : { mode: null, activeTabText: null, tabTexts: [] };
    
    let primaryText = '';
    let timeline = [];
    
    if (isTweetDetail) {
      primaryText = cleanXPrimaryText(article, tweetText);
    } else if (isTimeline) {
      timeline = extractXTimeline();
    } else {
      primaryText = cleanXPrimaryText(article, tweetText);
      timeline = extractXTimeline();
    }

    const network = getRequestProbeState();
    const networkQuiet = !network || network.pending === 0 && (network.quietMs === null || network.quietMs > 800);
    const ready = !!(
      document.readyState === 'complete' &&
      ((isTweetDetail && primaryText.length > 20) || (isTimeline && timeline.length > 0) || (!isTweetDetail && !isTimeline && document.body.innerText.length > 100)) &&
      !loginMask &&
      networkQuiet
    );
    return {
      site: 'x',
      page: base.page,
      signals: {
        ...base.signals,
        isX: true,
        isTweetDetail,
        isTimeline,
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
      },
    };
  },
};

function getActiveAdapter() {
  const adapters = [xAdapter, genericAdapter];
  return adapters.find((adapter) => adapter.match()) || genericAdapter;
}

function collectActiveSiteSnapshot() {
  return getActiveAdapter().collect();
}
