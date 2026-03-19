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
  const timeline = [];
  for (const cell of cells) {
    const tweetEl = cell.querySelector('[data-testid="tweet"]');
    if (!tweetEl) continue;
    const walker = document.createTreeWalker(tweetEl, NodeFilter.SHOW_TEXT, null, false);
    const fragments = [];
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
      if (text.length < 20 && /^(查看|显示)\s*(更多|回复|相关|此对话)/.test(text)) continue;
      fragments.push(text);
    }
    const timeEl = tweetEl.querySelector('time');
    const url = timeEl ? timeEl.parentElement.href : null;
    const authorEl = tweetEl.querySelector('[data-testid="User-Name"]');
    const authorInfo = authorEl ? authorEl.innerText.replace(/\n/g, ' ') : '';
    const filtered = [];
    for (let i = 0; i < fragments.length; i++) {
      if (i > 0 && fragments[i] === fragments[i-1]) continue;
      filtered.push(fragments[i]);
    }
    const textContent = filtered.join('\n\n').replace(/\n{4,}/g, '\n\n\n').trim();
    if (textContent.length > 0) {
       timeline.push({ authorInfo, url, text: textContent });
    }
  }
  return timeline;
}

const xAdapter = {
  id: 'x',
  match() {
    return location.hostname.includes('x.com') || location.hostname.includes('twitter.com');
  },
  collect() {
    const base = collectGenericSnapshot();
    const article = document.querySelector('article');
    const tweetText = document.querySelector('[data-testid="tweetText"]');
    const loginMask = !!document.querySelector('[role="dialog"], [data-testid="sheetDialog"]');
    const sensitiveGate = /(敏感内容|sensitive content|age-restricted|成人内容|adult content)/i.test(document.body?.innerText || '');
    
    const isTweetDetail = /\/status\/\d+/.test(location.href);
    const isTimeline = location.pathname === '/home' || location.pathname.startsWith('/search') || location.pathname.startsWith('/explore');
    
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
