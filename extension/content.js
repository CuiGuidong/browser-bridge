// Content script - injected into all pages
// Owns page-level observation and reports structured signals to background.

console.log('[Browser Bridge] Content script loaded');

(function installRequestProbe() {
  if (window.__BROWSER_BRIDGE_REQUEST_PROBE_INSTALLED__) return;
  window.__BROWSER_BRIDGE_REQUEST_PROBE_INSTALLED__ = true;

  const script = document.createElement('script');
  script.textContent = `
    (() => {
      if (window.__BROWSER_BRIDGE_PAGE_PROBE__) return;
      const state = {
        pending: 0,
        lastRequestStartedAt: 0,
        lastRequestFinishedAt: 0,
        requestCount: 0,
      };
      const publish = () => {
        const payload = JSON.stringify({
          pending: state.pending,
          requestCount: state.requestCount,
          lastRequestStartedAt: state.lastRequestStartedAt,
          lastRequestFinishedAt: state.lastRequestFinishedAt,
          quietMs: state.lastRequestFinishedAt ? Date.now() - state.lastRequestFinishedAt : null,
        });
        document.documentElement?.setAttribute('data-browser-bridge-probe', payload);
      };
      const start = () => {
        state.pending += 1;
        state.requestCount += 1;
        state.lastRequestStartedAt = Date.now();
        publish();
      };
      const finish = () => {
        state.pending = Math.max(0, state.pending - 1);
        state.lastRequestFinishedAt = Date.now();
        publish();
      };

      const origFetch = window.fetch;
      window.fetch = async function(...args) {
        start();
        try { return await origFetch.apply(this, args); }
        finally { finish(); }
      };

      const origOpen = XMLHttpRequest.prototype.open;
      const origSend = XMLHttpRequest.prototype.send;
      XMLHttpRequest.prototype.open = function(...args) {
        this.__bb_tracked = true;
        return origOpen.apply(this, args);
      };
      XMLHttpRequest.prototype.send = function(...args) {
        if (this.__bb_tracked) {
          start();
          this.addEventListener('loadend', finish, { once: true });
        }
        return origSend.apply(this, args);
      };

      window.__BROWSER_BRIDGE_PAGE_PROBE__ = {
        getState() {
          return {
            pending: state.pending,
            requestCount: state.requestCount,
            lastRequestStartedAt: state.lastRequestStartedAt,
            lastRequestFinishedAt: state.lastRequestFinishedAt,
            quietMs: state.lastRequestFinishedAt ? Date.now() - state.lastRequestFinishedAt : null,
          };
        }
      };
      publish();
    })();
  `;
  (document.documentElement || document.head || document.body).appendChild(script);
  script.remove();
})();

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

function cleanXPrimaryText(article, tweetText) {
  const container = article || document.querySelector('[data-testid="tweetText"]')?.closest('[role="article"]') || document.body;
  
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
  const fragments = [];
  const standaloneNoiseRegex = /^(主页|探索|通知|聊天|Grok|书签|更多|发帖|文章|对话|查看新帖子|订阅|分享|Home|Explore|Notifications|Messages|Bookmarks|More|Post|Articles|Subscribe|Share|什么是新鲜事|What’s happening)$/i;

  let node;
  while(node = walker.nextNode()) {
    const parent = node.parentElement;
    if (!parent) continue;
    
    const style = window.getComputedStyle(parent);
    if (style.display === 'none' || style.visibility === 'hidden') continue;
    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'NAV', 'HEADER'].includes(parent.tagName)) continue;

    const text = node.nodeValue.trim();
    if (text.length < 2) continue;
    
    if (text.length < 20 && standaloneNoiseRegex.test(text)) continue;
    if (text.length < 15 && /^[\d\,\.]+([KMBkmb万亿]?)$/.test(text)) continue;
    if (text.length < 20 && /^(查看|显示)\s*(更多|回复|相关|此对话)/.test(text)) continue;

    fragments.push(text);
  }

  const filtered = [];
  for (let i = 0; i < fragments.length; i++) {
    if (i > 0 && fragments[i] === fragments[i-1]) continue;
    filtered.push(fragments[i]);
  }

  let result = filtered.join('\n\n').replace(/\n{4,}/g, '\n\n\n').trim();
  return result || tweetText?.innerText?.trim() || '';
}

function extractXTimeline() {
  const cells = Array.from(document.querySelectorAll('[data-testid="cellInnerDiv"]'));
  const directTweets = Array.from(document.querySelectorAll('[data-testid="tweet"]'));
  const articleTweets = Array.from(
    document.querySelectorAll('article[role="article"]')
  ).filter((el) => {
    // Home/search feeds are noisy. Keep only article nodes that look like tweet cards.
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

  // Primary path: cell -> tweet, fallback paths: direct tweet and article cards.
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

      // Prefer explicit tweetText blocks for cleaner body formatting.
      const tweetTextNodes = Array.from(tweetEl.querySelectorAll('[data-testid="tweetText"]'));
      const bodyFromTweetText = tweetTextNodes
        .map((el) => (el.innerText || '').trim())
        .filter(Boolean)
        .join('\n\n')
        .replace(/\n{4,}/g, '\n\n\n')
        .trim();

      let textContent = bodyFromTweetText;
      const fragments = [];
      if (!textContent) {
        const walker = document.createTreeWalker(tweetEl, NodeFilter.SHOW_TEXT, null, false);
        let node;
        while(node = walker.nextNode()) {
          const parent = node.parentElement;
          if (!parent) continue;
          const style = window.getComputedStyle(parent);
          if (style.display === 'none' || style.visibility === 'hidden') continue;
          if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'NAV', 'HEADER'].includes(parent.tagName)) continue;
          const text = node.nodeValue.trim();
          if (text.length < 2) continue;
          if (text.length < 15 && /^[\d\,\.]+([KMBkmb万亿]?)$/.test(text)) continue;
          if (text.length < 20 && /^(查看|显示)\s*(更多|回复|相关|此对话|Show more)/i.test(text)) continue;
          fragments.push(text);
        }

        const filtered = [];
        for (let i = 0; i < fragments.length; i++) {
          if (i > 0 && fragments[i] === fragments[i-1]) continue;
          filtered.push(fragments[i]);
        }
        textContent = filtered.join('\n\n').replace(/\n{4,}/g, '\n\n\n').trim();
      }

      if (textContent.length > 0) {
         timeline.push({ authorInfo, publishedAt, publishedLabel, url, text: textContent });
      } else {
         timeline.push({ authorInfo, publishedAt, publishedLabel, url, text: "EMPTY_TEXT_FRAGMENTS", debug: fragments });
      }
    } catch (err) {
      console.warn('[Browser Bridge] Failed to parse a tweet in timeline', err);
      timeline.push({ error: err.toString(), message: err.message, stack: err.stack });
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

function collectXSnapshot(base) {
  const article = document.querySelector('article');
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
    // Fallback for other pages like profiles
    primaryText = cleanXPrimaryText(article, tweetText);
    timeline = extractXTimeline();
  }

  const network = getRequestProbeState();
  const networkQuiet = !network || (network.pending === 0 && (network.quietMs === null || network.quietMs > 800));
  
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
}

function collectSnapshot() {
  const base = collectGenericSnapshot();
  if (location.hostname.includes('x.com') || location.hostname.includes('twitter.com')) {
    return collectXSnapshot(base);
  }
  return base;
}

function reportSnapshot(kind = 'page-state') {
  const payload = {
    action: 'extensionSnapshot',
    payload: {
      source: 'extension',
      site: collectSnapshot().site,
      kind,
      ...collectSnapshot(),
    },
  };
  chrome.runtime.sendMessage(payload, () => void chrome.runtime.lastError);
}

let observer = null;
function startObservation() {
  if (observer) observer.disconnect();
  let lastReady = false;
  observer = new MutationObserver(() => {
    const snap = collectSnapshot();
    if (snap.signals.ready || snap.signals.bodyTextLength > 0) {
      reportSnapshot('mutation');
      if (snap.signals.ready && !lastReady) {
        lastReady = true;
      }
    }
  });
  observer.observe(document.documentElement || document.body, {
    childList: true,
    subtree: true,
    attributes: false,
  });

  let count = 0;
  const timer = setInterval(() => {
    count += 1;
    reportSnapshot('interval');
    const snap = collectSnapshot();
    if (snap.signals.ready || count >= 12) clearInterval(timer);
  }, 1500);
}

window.addEventListener('message', (event) => {
  if (event.source !== window) return;
  if (event.data.type && event.data.type === 'BROWSER_BRIDGE_REQUEST') {
    chrome.runtime.sendMessage(event.data.payload, (response) => {
      window.postMessage({
        type: 'BROWSER_BRIDGE_RESPONSE',
        id: event.data.id,
        response: response,
      }, '*');
    });
  }
});

document.dispatchEvent(new CustomEvent('browserBridgeReady', {
  detail: { version: '1.0.0' }
}));

reportSnapshot('initial');
startObservation();
