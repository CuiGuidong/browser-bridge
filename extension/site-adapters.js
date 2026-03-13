// Site adapter registry for Browser Bridge Extension

function getRequestProbeState() {
  try {
    return window.__BROWSER_BRIDGE_PAGE_PROBE__?.getState?.() || null;
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
    const sensitiveGate = !!Array.from(document.querySelectorAll('span,div')).find((el) =>
      /显示|查看|敏感|sensitive/i.test((el.innerText || '').trim())
    );
    const primaryText = (tweetText?.innerText || article?.innerText || '').trim();
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
