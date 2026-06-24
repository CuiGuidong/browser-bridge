// Xiaohongshu Adapter for Browser Bridge

function isXiaohongshuHost() {
  return location.hostname.includes('xiaohongshu.com');
}

function isCreatorPublishPage() {
  return location.hostname === 'creator.xiaohongshu.com' && location.pathname.startsWith('/publish/publish');
}

function normalizeMultilineText(value) {
  return (value || '')
    .replace(/\u00a0/g, ' ')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .split('\n')
    .map((line) => line.trim())
    .join('\n')
    .trim();
}

function shortText(value, maxLength = 160) {
  return (value || '').replace(/\s+/g, ' ').trim().slice(0, maxLength);
}

function parseMetricValue(value) {
  const text = String(value || '').replace(/,/g, '').trim();
  if (!text || text === '赞' || text === '回复' || text === '评论') return null;
  const match = text.match(/([\d.]+)\s*(万|w|W|千|k|K)?/);
  if (!match) return null;
  const number = Number(match[1]);
  if (!Number.isFinite(number)) return null;
  const unit = match[2] || '';
  if (unit === '万' || unit === 'w' || unit === 'W') return Math.round(number * 10000);
  if (unit === '千' || unit === 'k' || unit === 'K') return Math.round(number * 1000);
  return Math.round(number);
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getElementVisualScore(el) {
  if (!el) return -1;
  const rect = el.getBoundingClientRect();
  const style = window.getComputedStyle(el);
  const visible = rect.width > 0
    && rect.height > 0
    && style.visibility !== 'hidden'
    && style.display !== 'none'
    && style.opacity !== '0';
  return visible ? (rect.width * rect.height) : -1;
}

function findExactTextButton(text) {
  return Array.from(document.querySelectorAll('button, [role="button"]'))
    .find((el) => shortText(el.innerText, 40) === text);
}

function isElementDisabled(el) {
  if (!el) return true;
  const ariaDisabled = (el.getAttribute('aria-disabled') || '').toLowerCase();
  return !!(el.disabled || ariaDisabled === 'true' || /\bdisabled\b/i.test((el.className || '').toString()));
}

function normalizeCreatorTabKey(label) {
  const text = shortText(label, 40);
  if (text === 'image' || text === 'video' || text === 'article') return text;
  if (text.includes('上传图文')) return 'image';
  if (text.includes('上传视频')) return 'video';
  if (text.includes('写长文')) return 'article';
  return null;
}

function getCreatorTabElements() {
  return Array.from(document.querySelectorAll('.creator-tab'))
    .filter((el) => {
      const rect = el.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && rect.top > -1000 && rect.left > -1000;
    });
}

function getCreatorTabs() {
  return getCreatorTabElements()
    .map((el) => ({
      key: normalizeCreatorTabKey(el.innerText || ''),
      text: shortText(el.innerText || '', 40),
      active: /\bactive\b/i.test((el.className || '').toString()),
      className: shortText((el.className || '').toString(), 160),
    }))
    .filter((item) => item.key);
}

function getActiveCreatorTab() {
  const tabs = getCreatorTabs();
  const active = [...tabs].reverse().find((item) => item.active);
  return active ? active.key : null;
}

function getCreatorTabElementByKey(key) {
  return [...getCreatorTabElements()]
    .reverse()
    .find((el) => normalizeCreatorTabKey(el.innerText || '') === key);
}

function getCreatorImageInput() {
  return Array.from(document.querySelectorAll('input[type="file"]'))
    .find((el) => (el.getAttribute('accept') || '').includes('.jpg'));
}

function getCreatorVideoInput() {
  return Array.from(document.querySelectorAll('input[type="file"]'))
    .find((el) => (el.getAttribute('accept') || '').includes('.mp4'));
}

function getCreatorTitleInput() {
  const candidates = Array.from(document.querySelectorAll('input[placeholder*="标题"]'));
  return candidates
    .sort((a, b) => getElementVisualScore(b) - getElementVisualScore(a))[0] || null;
}

function getCreatorContentEditor() {
  const candidates = Array.from(
    document.querySelectorAll('.tiptap.ProseMirror[contenteditable="true"], .tiptap.ProseMirror, [contenteditable="true"]'),
  );
  return candidates
    .sort((a, b) => getElementVisualScore(b) - getElementVisualScore(a))[0] || null;
}

function getCreatorPublishButton() {
  return findExactTextButton('发布');
}

function getCreatorSaveButton() {
  return findExactTextButton('暂存离开');
}

function getCreatorImageUploadSelector() {
  return 'input[type="file"][accept*=".jpg"]';
}

function getCreatorPublishPageType() {
  if (!isCreatorPublishPage()) return null;
  const tabs = getCreatorTabs();
  const titleInput = getCreatorTitleInput();
  const editor = getCreatorContentEditor();
  const publishButton = getCreatorPublishButton();
  if (titleInput && editor && publishButton) {
    return 'creator_publish_editor_image';
  }
  if (tabs.length > 0) {
    return 'creator_publish_entry';
  }
  return 'creator_publish';
}

function collectCreatorPublishState() {
  if (!isCreatorPublishPage()) return null;
  const pageType = getCreatorPublishPageType();
  const tabs = getCreatorTabs();
  const imageInput = getCreatorImageInput();
  const videoInput = getCreatorVideoInput();
  const titleInput = getCreatorTitleInput();
  const editor = getCreatorContentEditor();
  const publishButton = getCreatorPublishButton();
  const saveButton = getCreatorSaveButton();
  let activeTab = null;
  if (pageType === 'creator_publish_editor_image') {
    activeTab = 'image';
  } else if (imageInput && !videoInput) {
    activeTab = 'image';
  } else if (videoInput && !imageInput) {
    activeTab = 'video';
  } else {
    activeTab = getActiveCreatorTab();
  }
  const titleValue = titleInput ? (titleInput.value || '') : '';
  const editorText = editor ? normalizeMultilineText(editor.innerText || editor.textContent || '') : '';

  return {
    pageType,
    activeTab,
    tabs,
    imageUpload: {
      exists: !!imageInput,
      selector: imageInput ? getCreatorImageUploadSelector() : null,
      accept: imageInput ? (imageInput.getAttribute('accept') || '') : '',
      multiple: !!imageInput?.multiple,
      fileCount: imageInput?.files ? imageInput.files.length : 0,
      firstFileName: imageInput?.files?.[0]?.name || null,
    },
    videoUpload: {
      exists: !!videoInput,
      accept: videoInput ? (videoInput.getAttribute('accept') || '') : '',
      multiple: !!videoInput?.multiple,
    },
    titleInput: {
      exists: !!titleInput,
      placeholder: titleInput ? (titleInput.getAttribute('placeholder') || '') : '',
      value: titleValue,
      length: titleValue.length,
    },
    contentEditor: {
      exists: !!editor,
      text: editorText,
      length: editorText.length,
      className: shortText((editor?.className || '').toString(), 160),
    },
    publishButton: {
      exists: !!publishButton,
      disabled: isElementDisabled(publishButton),
      text: shortText(publishButton?.innerText || '', 40),
    },
    saveButton: {
      exists: !!saveButton,
      disabled: isElementDisabled(saveButton),
      text: shortText(saveButton?.innerText || '', 40),
    },
  };
}

function setNativeInputValue(input, value) {
  if (!input) return;
  const descriptor = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
  if (descriptor && descriptor.set) {
    descriptor.set.call(input, value);
  } else {
    input.value = value;
  }
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
}

function replaceContentEditableText(editor, value) {
  if (!editor) return false;
  const normalized = String(value || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  editor.focus();

  const selection = window.getSelection();
  const range = document.createRange();
  range.selectNodeContents(editor);
  selection.removeAllRanges();
  selection.addRange(range);

  let execSucceeded = false;
  try {
    document.execCommand('selectAll', false, null);
    execSucceeded = document.execCommand('insertText', false, normalized);
  } catch {
    execSucceeded = false;
  }

  if (!execSucceeded) {
    editor.innerHTML = '';
    const lines = normalized.split('\n');
    for (const line of lines) {
      const p = document.createElement('p');
      if (line) {
        p.textContent = line;
      } else {
        p.appendChild(document.createElement('br'));
      }
      editor.appendChild(p);
    }
    try {
      editor.dispatchEvent(new InputEvent('beforeinput', {
        bubbles: true,
        cancelable: true,
        inputType: 'insertText',
        data: normalized,
      }));
      editor.dispatchEvent(new InputEvent('input', {
        bubbles: true,
        inputType: 'insertText',
        data: normalized,
      }));
    } catch {
      editor.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }

  editor.dispatchEvent(new Event('change', { bubbles: true }));
  return true;
}

function getXiaohongshuPageType() {
  const creatorPageType = getCreatorPublishPageType();
  if (creatorPageType) return creatorPageType;
  const path = location.pathname || '';
  if (/^\/explore\/[A-Za-z0-9]+/.test(path)) return 'post';
  if (/^\/user\/profile\/[A-Za-z0-9]+/.test(path)) return 'profile';
  if (path === '/explore') return 'home';
  if (path.startsWith('/search_result')) return 'search';
  return 'other';
}

function normalizeXiaohongshuUrl(url) {
  if (!url) return '';
  try {
    const parsed = new URL(url, location.origin);
    // Keep query string for note-detail URLs so xsec_token/xsec_source
    // can be reused in follow-up read_post calls.
    if (/^\/explore\/[A-Za-z0-9]+/.test(parsed.pathname || '')) {
      return `${parsed.origin}${parsed.pathname}${parsed.search || ''}`;
    }
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
  const links = Array.from(card.querySelectorAll('a[href*="/explore/"]'));
  if (!links.length) return null;

  // Prefer the signed detail link so follow-up read_post can keep xsec_token.
  const preferred = links.find((a) => {
    try {
      const parsed = new URL(a.href, location.origin);
      return parsed.searchParams.has('xsec_token');
    } catch {
      return false;
    }
  }) || links[0];

  return normalizeXiaohongshuUrl(preferred.href);
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

function extractPostAuthorProfileUrl() {
  const author = extractPostAuthor();
  const links = Array.from(document.querySelectorAll('a[href*="/user/profile/"]'));
  const byName = links.find((link) => shortText(link.innerText || '', 80) === author);
  const byNoteSource = links.find((link) => {
    try {
      const parsed = new URL(link.href, location.origin);
      return parsed.searchParams.get('xsec_source') === 'pc_note';
    } catch {
      return false;
    }
  });
  return normalizeXiaohongshuUrl((byName || byNoteSource || links[0])?.href || '');
}

function extractPostIdFromUrl(url) {
  try {
    const parsed = new URL(url || location.href, location.origin);
    const parts = parsed.pathname.split('/').filter(Boolean);
    if (parts[0] === 'explore' && parts[1]) return parts[1];
  } catch {
    return null;
  }
  return null;
}

function extractPostMetrics() {
  const container = document.querySelector('.interact-container');
  const readWrapperCount = (selector) => {
    const el = container?.querySelector(selector) || document.querySelector(selector);
    return parseMetricValue(el?.innerText || el?.textContent || '');
  };
  return {
    views: null,
    likes: readWrapperCount('.like-wrapper'),
    comments: readWrapperCount('.chat-wrapper'),
    shares: null,
    favorites: readWrapperCount('.collect-wrapper'),
  };
}

function extractPostImages() {
  const images = Array.from(document.querySelectorAll('img'))
    .map((img) => img.currentSrc || img.src || '')
    .filter((src) => src && /^https?:/i.test(src))
    .filter((src) => /sns-webpic.*xhscdn\.com/i.test(src))
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
  return baseText.trim();
}

function normalizeCommentLimit(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 20;
  return Math.min(Math.max(Math.floor(parsed), 0), 100);
}

function detectCommentsUnavailableReason() {
  const text = (document.body?.innerText || '').trim();
  if (!text) return 'not_loaded';
  if (/评论加载失败|评论暂时无法显示|无法查看评论|登录后查看评论/.test(text)) return 'not_loaded';
  return null;
}

function extractVisiblePostComments(limit = 20) {
  limit = normalizeCommentLimit(limit);
  if (limit <= 0) return [];
  const seen = new Set();
  const roots = Array.from(document.querySelectorAll('.comment-item, [class*="comment-item"], [class*="CommentItem"]'))
    .filter((root) => !/\bcomment-item-sub\b/.test((root.className || '').toString()));
  const comments = [];
  for (const root of roots) {
    if (comments.length >= limit) break;
    const rawText = normalizeMultilineText(root.innerText || '');
    if (!rawText || rawText.length < 2 || rawText.length > 800) continue;
    if (/(广告|推广|推荐)/.test(rawText)) continue;
    const lines = rawText.split('\n').map((line) => line.trim()).filter(Boolean);
    const authorName = shortText(root.querySelector('.author .name, .name')?.innerText || lines[0] || '', 80) || null;
    const time = shortText(root.querySelector('.date')?.innerText || '', 80)
      || lines.find((line) => /(\d+分钟前|\d+小时前|\d+天前|昨天|今天|\d{1,2}-\d{1,2})/.test(line))
      || null;
    const likesText = shortText(root.querySelector('.interactions .like .count, .like .count')?.innerText || '', 40);
    const repliesText = shortText(root.querySelector('.interactions .reply .count, .reply .count')?.innerText || '', 40);
    const structuredText = normalizeMultilineText(root.querySelector('.content')?.innerText || '');
    const text = structuredText || lines
      .filter((line) => line !== authorName)
      .filter((line) => line !== time)
      .filter((line) => line !== likesText)
      .filter((line) => line !== repliesText)
      .filter((line) => !/^(赞|回复|作者|置顶评论|作者赞过)$/.test(line))
      .filter((line) => !/^展开\d*条?回复$/.test(line))
      .join('\n')
      .trim();
    if (!text || text.length < 2 || text.length > 600) continue;
    if (/(广告|推广|推荐)/.test(text)) continue;
    const key = text.slice(0, 120);
    if (seen.has(key)) continue;
    seen.add(key);
    comments.push({
      authorName,
      time,
      text,
      media: [],
      metrics: {
        likes: parseMetricValue(likesText),
        comments: null,
        replies: parseMetricValue(repliesText),
      },
      platformMetrics: {},
    });
  }
  return comments;
}

function extractPostContent(commentLimit = 20) {
  const postImages = extractPostImages();
  const postVideos = extractPostVideos();
  const postComments = extractVisiblePostComments(commentLimit);
  return {
    title: extractPostTitle(),
    author: extractPostAuthor(),
    authorProfileUrl: extractPostAuthorProfileUrl(),
    externalPostId: extractPostIdFromUrl(location.href),
    text: extractPostText(postImages, postVideos),
    images: postImages,
    videos: postVideos,
    metrics: extractPostMetrics(),
    comments: postComments,
    commentsUnavailableReason: postComments.length ? null : detectCommentsUnavailableReason(),
    url: normalizeXiaohongshuUrl(location.href),
  };
}

function extractProfileIdFromUrl(url) {
  try {
    const parsed = new URL(url || location.href, location.origin);
    const parts = parsed.pathname.split('/').filter(Boolean);
    if (parts[0] === 'user' && parts[1] === 'profile' && parts[2]) return parts[2];
  } catch {
    return null;
  }
  return null;
}

function extractProfileNickname() {
  const userName = document.querySelector('.user-name');
  const text = shortText(userName?.innerText || '', 120);
  if (text) return text;
  const title = (document.title || '').replace(/\s*-\s*小红书\s*$/, '').trim();
  return title || '';
}

function extractProfileDescription() {
  return normalizeMultilineText(document.querySelector('.user-desc')?.innerText || '');
}

function extractProfileTags() {
  const tags = document.querySelector('.user-tags');
  return (tags?.innerText || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
}

function extractProfileMetrics() {
  const info = document.querySelector('.data-info');
  const lines = (info?.innerText || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  const valueBeforeLabel = (label) => {
    const index = lines.findIndex((line) => line === label);
    if (index <= 0) return null;
    return parseMetricValue(lines[index - 1]);
  };
  return {
    followers: valueBeforeLabel('粉丝'),
    following: valueBeforeLabel('关注'),
    likes: valueBeforeLabel('获赞与收藏'),
    postsCount: null,
  };
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
      read: [
        'read_post',
        'read_home',
        'search',
        'read_creator_publish_state',
        'read_post_metrics',
        'read_profile_metrics',
        'account_status',
      ],
      act: [
        'switch_creator_tab',
        'locate_creator_image_file_input',
        'fill_creator_title',
        'fill_creator_content',
        'assert_ready_before_publish',
      ],
    };
  },
  collect(baseSnapshot) {
    const pageType = getXiaohongshuPageType();
    const creatorPublishState = pageType.startsWith('creator_publish')
      ? collectCreatorPublishState()
      : null;
    const noteItems = collectFeedItems();
    const detailDesc = document.querySelector('#detail-desc');
    const post = pageType === 'post' ? extractPostContent() : null;
    const postImages = post ? post.images : [];
    const hasVideo = pageType === 'post' ? detectHasVideo() : false;
    const ready = !!(
      document.readyState === 'complete' && (
        (pageType === 'post' && ((detailDesc && (detailDesc.innerText || '').trim().length > 0) || postImages.length > 0 || hasVideo)) ||
        (pageType === 'profile' && !!document.querySelector('.user-info')) ||
        ((pageType === 'home' || pageType === 'search') && noteItems.length > 0) ||
        ((pageType === 'creator_publish_entry') && (creatorPublishState?.tabs || []).length > 0) ||
        ((pageType === 'creator_publish_editor_image') && !!creatorPublishState?.titleInput?.exists && !!creatorPublishState?.contentEditor?.exists && !!creatorPublishState?.publishButton?.exists) ||
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
        profileReady: pageType === 'profile' && !!document.querySelector('.user-info'),
        activeCreatorTab: creatorPublishState?.activeTab || null,
        creatorTabs: creatorPublishState?.tabs || [],
        creatorEditorReady: !!creatorPublishState?.contentEditor?.exists,
      },
      content: {
        items: noteItems,
        post,
        profile: pageType === 'profile' ? {
          url: normalizeXiaohongshuUrl(location.href),
          profileId: extractProfileIdFromUrl(location.href),
          nickname: extractProfileNickname(),
          description: extractProfileDescription(),
          tags: extractProfileTags(),
          metrics: extractProfileMetrics(),
          recentPosts: noteItems,
        } : null,
        creatorPublishState,
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
      const commentLimit = normalizeCommentLimit(_params?.commentLimit);
      return {
        ok: true,
        mode: 'semantic',
        kind,
        page: snap.page,
        signals: snap.signals,
        content: extractPostContent(commentLimit),
      };
    }
    if (kind === 'read_post_metrics') {
      const post = snap.content.post || {};
      return {
        ok: true,
        mode: 'semantic',
        kind,
        page: snap.page,
        signals: snap.signals,
        content: {
          url: post.url || normalizeXiaohongshuUrl(location.href),
          externalPostId: post.externalPostId || extractPostIdFromUrl(location.href),
          title: post.title || '',
          author: post.author || '',
          authorProfileUrl: post.authorProfileUrl || '',
          metrics: post.metrics || extractPostMetrics(),
          rawPayload: {
            pageType: snap.signals.pageType,
          },
        },
      };
    }
    if (kind === 'read_profile_metrics') {
      const profile = snap.content.profile || {};
      return {
        ok: true,
        mode: 'semantic',
        kind,
        page: snap.page,
        signals: snap.signals,
        content: {
          url: profile.url || normalizeXiaohongshuUrl(location.href),
          profileId: profile.profileId || extractProfileIdFromUrl(location.href),
          nickname: profile.nickname || '',
          description: profile.description || '',
          tags: profile.tags || [],
          metrics: profile.metrics || extractProfileMetrics(),
          recentPosts: profile.recentPosts || [],
          rawPayload: {
            pageType: snap.signals.pageType,
          },
        },
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
    if (kind === 'read_creator_publish_state') {
      return {
        ok: true,
        mode: 'semantic',
        kind,
        page: snap.page,
        signals: snap.signals,
        content: snap.content.creatorPublishState || {},
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
    if (kind === 'switch_creator_tab') {
      const targetTab = normalizeCreatorTabKey(params.tab || params.target || 'image');
      const before = snap.content.creatorPublishState || {};
      if (!targetTab) {
        return {
          ok: false,
          action: kind,
          page: snap.page,
          signals: snap.signals,
          error: 'invalid creator tab',
        };
      }
      const tabEl = getCreatorTabElementByKey(targetTab);
      if (!tabEl) {
        return {
          ok: false,
          action: kind,
          page: snap.page,
          signals: snap.signals,
          error: 'creator tab not found',
        };
      }
      if ((before.activeTab || null) !== targetTab) {
        tabEl.click();
        await wait(1000);
      }
      return {
        ok: true,
        action: kind,
        changed: (before.activeTab || null) !== targetTab,
        before: {
          activeTab: before.activeTab || null,
          pageType: before.pageType || null,
        },
      };
    }
    if (kind === 'locate_creator_image_file_input') {
      const state = snap.content.creatorPublishState || {};
      if (state.activeTab !== 'image' && state.pageType !== 'creator_publish_editor_image') {
        return {
          ok: false,
          action: kind,
          page: snap.page,
          signals: snap.signals,
          error: 'creator page is not in image flow',
        };
      }
      if (!state.imageUpload?.exists) {
        return {
          ok: false,
          action: kind,
          page: snap.page,
          signals: snap.signals,
          error: 'image file input not found',
        };
      }
      return {
        ok: true,
        action: kind,
        changed: false,
        before: {
          activeTab: state.activeTab || null,
          pageType: state.pageType || null,
        },
        selector: state.imageUpload.selector,
      };
    }
    if (kind === 'fill_creator_title') {
      const text = String(params.text || '');
      const input = getCreatorTitleInput();
      if (!input) {
        return {
          ok: false,
          action: kind,
          page: snap.page,
          signals: snap.signals,
          error: 'creator title input not found',
        };
      }
      const beforeValue = input.value || '';
      input.focus();
      setNativeInputValue(input, text);
      await wait(150);
      input.blur();
      await wait(150);
      return {
        ok: true,
        action: kind,
        changed: beforeValue !== text,
        before: {
          value: beforeValue,
        },
      };
    }
    if (kind === 'fill_creator_content') {
      const text = String(params.text || '');
      const editor = getCreatorContentEditor();
      if (!editor) {
        return {
          ok: false,
          action: kind,
          page: snap.page,
          signals: snap.signals,
          error: 'creator content editor not found',
        };
      }
      const beforeText = normalizeMultilineText(editor.innerText || editor.textContent || '');
      replaceContentEditableText(editor, text);
      await wait(300);
      return {
        ok: true,
        action: kind,
        changed: beforeText !== normalizeMultilineText(text),
        before: {
          text: beforeText,
        },
      };
    }
    if (kind === 'assert_ready_before_publish') {
      const state = snap.content.creatorPublishState || {};
      return {
        ok: true,
        action: kind,
        changed: false,
        before: {
          pageType: state.pageType || null,
          activeTab: state.activeTab || null,
        },
      };
    }
    return {
      ok: false,
      action: kind,
      page: snap.page,
      signals: snap.signals,
      error: `Unsupported action kind: ${kind}`,
    };
  },
  async verify(kind, params, context, actionResult) {
    const snap = this.collect(context.baseSnapshot);
    const state = snap.content.creatorPublishState || {};
    if (kind === 'switch_creator_tab') {
      const targetTab = normalizeCreatorTabKey(params.tab || params.target || 'image');
      return {
        ok: true,
        verified: state.activeTab === targetTab,
        after: {
          activeTab: state.activeTab || null,
          pageType: state.pageType || null,
        },
        actionResult,
      };
    }
    if (kind === 'locate_creator_image_file_input') {
      return {
        ok: true,
        verified: !!state.imageUpload?.exists && !!state.imageUpload?.selector,
        after: {
          activeTab: state.activeTab || null,
          pageType: state.pageType || null,
          selector: state.imageUpload?.selector || null,
          accept: state.imageUpload?.accept || '',
          multiple: !!state.imageUpload?.multiple,
        },
        actionResult,
      };
    }
    if (kind === 'fill_creator_title') {
      return {
        ok: true,
        verified: (state.titleInput?.value || '') === String(params.text || ''),
        after: {
          value: state.titleInput?.value || '',
          length: state.titleInput?.length || 0,
        },
        actionResult,
      };
    }
    if (kind === 'fill_creator_content') {
      const expectedText = normalizeMultilineText(String(params.text || ''));
      return {
        ok: true,
        verified: normalizeMultilineText(state.contentEditor?.text || '') === expectedText,
        after: {
          text: state.contentEditor?.text || '',
          length: state.contentEditor?.length || 0,
        },
        actionResult,
      };
    }
    if (kind === 'assert_ready_before_publish') {
      return {
        ok: true,
        verified: state.pageType === 'creator_publish_editor_image'
          && (state.titleInput?.length || 0) > 0
          && (state.contentEditor?.length || 0) > 0
          && !!state.publishButton?.exists,
        after: {
          pageType: state.pageType || null,
          activeTab: state.activeTab || null,
          titleLength: state.titleInput?.length || 0,
          contentLength: state.contentEditor?.length || 0,
          publishButton: state.publishButton || {},
        },
        actionResult,
      };
    }
    return {
      ok: true,
      verified: !!actionResult?.ok,
      actionResult,
    };
  },
};

window.BrowserBridgeAdapters = window.BrowserBridgeAdapters || [];
window.BrowserBridgeAdapters.push(xiaohongshuAdapter);
