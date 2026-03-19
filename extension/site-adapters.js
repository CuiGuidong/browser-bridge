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
      primaryText: text.slice(0, 4000),
    },
  };
}

const genericAdapter = {
  id: 'generic',
  match() {
    return true;
  },
  collect() {
    return collectGenericSnapshot();
  },
};

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
    
    let primaryText = '';
    if (article) {
      const clone = article.cloneNode(true);
      const noiseSelectors = ['button', 'nav', 'aside', 'svg', '[aria-hidden="true"]', '[data-testid="caret"]', '[data-testid="reply"]', '[data-testid="retweet"]', '[data-testid="like"]', '[data-testid="bookmark"]'];
      clone.querySelectorAll(noiseSelectors.join(', ')).forEach((el) => el.remove());
      primaryText = (clone.innerText || '').trim();
      const lines = primaryText.split('\n').map((s) => s.trim()).filter(Boolean);
      const filtered = [];
      for (const line of lines) {
        if (/^(主页|探索|通知|聊天|Grok|书签|更多|发帖|文章|对话|查看新帖子|订阅|分享)$/i.test(line)) continue;
        if (/^(Home|Explore|Notifications|Messages|Bookmarks|More|Post|Articles|Subscribe|Share)$/i.test(line)) continue;
        if (/^[\d\,\.]+([KMBkmb万亿]?)$/.test(line)) continue;
        if (/^(查看|显示)\s*(更多|回复|相关|此对话)/.test(line)) continue;
        if (/^Show (more|replies|this thread)/i.test(line)) continue;
        if (/^\s*回复\s*/.test(line)) continue;
        if (/^Replying to\s+/i.test(line)) continue;
        if (/点击\s*订阅\s*到/i.test(line)) continue;
        if (/^\d+[\d\,\.]*[KMBkmb万亿]?\s*(查看|Views?)$/i.test(line)) continue;
        filtered.push(line);
      }
      primaryText = filtered.join('\n').replace(/\n{3,}/g, '\n\n').trim();
    }
    if (!primaryText && tweetText) {
      primaryText = tweetText.innerText.trim();
    }

    const isTweetDetail = /\/status\/\d+/.test(location.href);
    const network = getRequestProbeState();
    const networkQuiet = !network || network.pending === 0 && (network.quietMs === null || network.quietMs > 800);
    const ready = !!(
      document.readyState === 'complete' &&
      isTweetDetail &&
      article &&
      primaryText.length > 20 &&
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
        articleFound: !!article,
        tweetTextFound: !!tweetText,
        loginMask,
        sensitiveGate,
        networkQuiet,
        ready,
      },
      content: {
        primaryText: primaryText.slice(0, 4000),
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
