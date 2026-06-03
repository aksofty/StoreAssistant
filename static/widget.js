(function () {
  'use strict';

  // --- Config ---
  const currentScript = document.currentScript || (function () {
    const scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  const src = currentScript.getAttribute('src') || '';
  const baseUrl = src.replace(/\/static\/widget\.js.*$/, '');
  const askUrl = baseUrl + '/ask';
  const historyUrl = baseUrl + '/chat_history';
  const cssUrl = baseUrl + '/static/widget.css?v=1.0.1';

  const ASSISTANT_NAME = currentScript.getAttribute('data-name') || 'Ассистент';
  const ASSISTANT_PICTURE = currentScript.getAttribute('data-picture') || '';
  const ASSISTANT_GREETING = currentScript.getAttribute('data-greeting') || 'Здравствуйте! Чем могу помочь?';

  const CATALOG_BREAKPOINT = 1024;

  // --- UID ---
  function getUID() {
    let uid = localStorage.getItem('rag_widget_uid');
    if (!uid) {
      uid = 'uid_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem('rag_widget_uid', uid);
    }
    return uid;
  }
  const UID = getUID();

  // --- Load CSS ---
  function loadCSS(href) {
    if (document.querySelector('link[data-rag-widget]')) return;
    // Инлайн-стиль скрывает элементы до загрузки внешнего CSS, чтобы не мелькали
    if (!document.querySelector('style[data-rag-critical]')) {
      const s = document.createElement('style');
      s.setAttribute('data-rag-critical', '1');
      s.textContent = '#rag-window,#rag-catalog{opacity:0!important;pointer-events:none!important}';
      document.head.appendChild(s);
    }
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    link.setAttribute('data-rag-widget', '1');
    link.onload = () => {
      const critical = document.querySelector('style[data-rag-critical]');
      if (critical) critical.remove();
    };
    document.head.appendChild(link);
  }
  loadCSS(cssUrl);

  // --- State ---
  let chatOpen = false;
  let currentOffers = [];
  let historyLoaded = false;

  function isLargeScreen() {
    return window.innerWidth >= CATALOG_BREAKPOINT;
  }

  // --- Avatar helpers ---
  const _svgPerson = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a5 5 0 1 0 0 10A5 5 0 0 0 12 2zM12 14c-5.33 0-8 2.67-8 4v1h16v-1c0-1.33-2.67-4-8-4z"/></svg>`;

  function avatarHtml() {
    if (ASSISTANT_PICTURE) {
      return `<img src="${escapeHtml(ASSISTANT_PICTURE)}" alt="${escapeHtml(ASSISTANT_NAME)}" class="rag-avatar-img">`;
    }
    return _svgPerson;
  }

  function botAvatarHtml() {
    if (ASSISTANT_PICTURE) {
      return `<img src="${escapeHtml(ASSISTANT_PICTURE)}" alt="${escapeHtml(ASSISTANT_NAME)}" class="rag-avatar-img">`;
    }
    return _svgPerson;
  }

  // --- Build HTML ---
  function buildWidget() {
    const wrapper = document.createElement('div');
    wrapper.id = 'rag-widget';
    wrapper.innerHTML = `
      <button id="rag-toggle" aria-label="Открыть чат">
        <svg id="rag-icon-chat" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        <svg id="rag-icon-close" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>

      <div id="rag-window">
        <div id="rag-header">
          <div id="rag-header-info">
            <div id="rag-avatar">${avatarHtml()}</div>
            <div>
              <div id="rag-name">${escapeHtml(ASSISTANT_NAME)}</div>
              <div id="rag-status"><span id="rag-status-dot"></span>Онлайн</div>
            </div>
          </div>
          <button id="rag-close-btn" aria-label="Закрыть">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div id="rag-messages"></div>

        <div id="rag-input-area">
          <textarea id="rag-input" placeholder="Напишите сообщение..." rows="1" maxlength="2000"></textarea>
          <button id="rag-send" aria-label="Отправить">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        </div>
      </div>
    `;
    // Catalog (inside widget — позиционируется левее чата)
    const catalog = document.createElement('div');
    catalog.id = 'rag-catalog';
    catalog.innerHTML = `
      <div id="rag-catalog-header">
        <span id="rag-catalog-title">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
            <path d="M19 6h-2c0-2.76-2.24-5-5-5S7 3.24 7 6H5c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-7-3c1.66 0 3 1.34 3 3H9c0-1.66 1.34-3 3-3zm0 10c-1.66 0-3-1.34-3-3h2c0 .55.45 1 1 1s1-.45 1-1h2c0 1.66-1.34 3-3 3z"/>
          </svg>
          Найденные товары
        </span>
        <button id="rag-catalog-close" aria-label="Закрыть каталог">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div id="rag-catalog-grid"></div>
    `;
    wrapper.appendChild(catalog);
    document.body.appendChild(wrapper);
  }

  // --- Render helpers ---
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Матчим: https?://... | www.... | домен.tld/путь (требуем слеш — меньше ложных срабатываний)
  const _URL_RE = /https?:\/\/[^\s<>"']+|www\.[^\s<>"']+|[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+\/[^\s<>"']*/g;

  function renderText(text) {
    const parts = [];
    let last = 0;
    _URL_RE.lastIndex = 0;
    let m;
    while ((m = _URL_RE.exec(text)) !== null) {
      // текст до ссылки
      if (m.index > last) parts.push(escapeHtml(text.slice(last, m.index)));

      let raw = m[0];
      // отрезаем замыкающую пунктуацию (.,;:!?)])
      const tail = raw.match(/[.,;:!?\])+]+$/);
      if (tail) raw = raw.slice(0, -tail[0].length);

      const href = /^https?:\/\//i.test(raw) ? raw : 'https://' + raw;
      parts.push(`<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer" class="rag-link">${escapeHtml(raw)}</a>`);

      // замыкающая пунктуация — как обычный текст
      if (tail) parts.push(escapeHtml(tail[0]));

      last = m.index + m[0].length;
    }
    if (last < text.length) parts.push(escapeHtml(text.slice(last)));
    return parts.join('').replace(/\n/g, '<br>');
  }

  // Inline mini-cards (mobile / fallback)
  function renderOffersInline(offers) {
    if (!offers || !offers.length) return '';
    const cards = offers.map(o => `
      <a class="rag-offer-card" href="${escapeHtml(o.url || '#')}" target="_blank" rel="noopener noreferrer">
        ${o.image_url ? `<div class="rag-offer-img"><img src="${escapeHtml(o.image_url)}" alt="${escapeHtml(o.title || '')}" loading="lazy"></div>` : ''}
        <div class="rag-offer-body">
          ${o.title ? `<div class="rag-offer-title">${escapeHtml(o.title)}</div>` : ''}
          ${o.price ? `<div class="rag-offer-price">${escapeHtml(o.price)}</div>` : ''}
          ${o.description ? `<div class="rag-offer-desc">${escapeHtml(o.description)}</div>` : ''}
        </div>
      </a>
    `).join('');
    return `<div class="rag-offers">${cards}</div>`;
  }

  // --- Catalog ---
  function updateCatalog(offers) {
    currentOffers = offers || [];
    const grid = document.getElementById('rag-catalog-grid');
    if (!grid) return;

    if (!currentOffers.length) {
      hideCatalog();
      return;
    }

    grid.innerHTML = currentOffers.map(o => `
      <a class="rag-cat-card" href="${escapeHtml(o.url || '#')}" target="_blank" rel="noopener noreferrer">
        ${o.image_url ? `<div class="rag-cat-img"><img src="${escapeHtml(o.image_url)}" alt="${escapeHtml(o.title || '')}" loading="lazy"></div>` : ''}
        <div class="rag-cat-body">
          ${o.title ? `<div class="rag-cat-title">${escapeHtml(o.title)}</div>` : ''}
          ${o.price ? `<div class="rag-cat-price">${escapeHtml(o.price)}</div>` : ''}
          ${o.description ? `<div class="rag-cat-desc">${escapeHtml(o.description)}</div>` : ''}
          ${o.url ? `<div class="rag-cat-link">Подробнее →</div>` : ''}
        </div>
      </a>
    `).join('');

    if (chatOpen && isLargeScreen()) {
      showCatalog();
    }
  }

  function showCatalog() {
    const el = document.getElementById('rag-catalog');
    if (el && currentOffers.length && isLargeScreen()) {
      el.classList.add('rag-catalog-open');
    }
  }

  function hideCatalog() {
    const el = document.getElementById('rag-catalog');
    if (el) el.classList.remove('rag-catalog-open');
  }

  // --- Messages ---
  // quiet=true: без анимации (для отрисовки истории)
  function addMessage(role, content, quiet) {
    const messages = document.getElementById('rag-messages');
    const row = document.createElement('div');
    row.className = 'rag-msg-row rag-msg-' + role;

    if (role === 'bot') {
      row.innerHTML = `
        <div class="rag-msg-avatar">${botAvatarHtml()}</div>
        <div class="rag-msg-bubble">
          <div class="rag-msg-text">${renderText(typeof content === 'string' ? content : '')}</div>
        </div>`;
    } else {
      row.innerHTML = `<div class="rag-msg-bubble"><div class="rag-msg-text">${renderText(content)}</div></div>`;
    }

    messages.appendChild(row);
    if (quiet) {
      row.classList.add('rag-msg-visible');
    } else {
      requestAnimationFrame(() => row.classList.add('rag-msg-visible'));
    }
    messages.scrollTop = messages.scrollHeight;
    return row;
  }

  // quiet=true: без анимации и без обновления каталога (история)
  function addBotResponse(data, quiet) {
    const messages = document.getElementById('rag-messages');
    const row = document.createElement('div');
    row.className = 'rag-msg-row rag-msg-bot';

    const hasOffers = data.offers && data.offers.length > 0;
    const offersInline = hasOffers && !isLargeScreen() ? renderOffersInline(data.offers) : '';

    // На большом экране показываем подсказку вместо карточек
    const offersHint = hasOffers && isLargeScreen()
      ? `<div class="rag-offers-hint">
           <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
             <path d="M19 6h-2c0-2.76-2.24-5-5-5S7 3.24 7 6H5c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-7-3c1.66 0 3 1.34 3 3H9c0-1.66 1.34-3 3-3zm0 10c-1.66 0-3-1.34-3-3h2c0 .55.45 1 1 1s1-.45 1-1h2c0 1.66-1.34 3-3 3z"/>
           </svg>
           ${data.offers.length} ${pluralOffers(data.offers.length)} — смотрите слева
         </div>`
      : '';

    row.innerHTML = `
      <div class="rag-msg-avatar">${botAvatarHtml()}</div>
      <div class="rag-msg-bubble">
        ${data.text ? `<div class="rag-msg-text">${renderText(data.text)}</div>` : ''}
        ${offersHint}
        ${offersInline}
      </div>`;

    messages.appendChild(row);
    if (quiet) {
      row.classList.add('rag-msg-visible');
    } else {
      requestAnimationFrame(() => row.classList.add('rag-msg-visible'));
    }
    messages.scrollTop = messages.scrollHeight;

    if (hasOffers && !quiet) updateCatalog(data.offers);
  }

  function pluralOffers(n) {
    if (n === 1) return 'товар';
    if (n >= 2 && n <= 4) return 'товара';
    return 'товаров';
  }

  function showTyping() {
    const messages = document.getElementById('rag-messages');
    const row = document.createElement('div');
    row.className = 'rag-msg-row rag-msg-bot rag-typing-row';
    row.innerHTML = `
      <div class="rag-msg-avatar">${botAvatarHtml()}</div>
      <div class="rag-msg-bubble rag-typing">
        <span></span><span></span><span></span>
      </div>`;
    messages.appendChild(row);
    requestAnimationFrame(() => row.classList.add('rag-msg-visible'));
    messages.scrollTop = messages.scrollHeight;
    return row;
  }

  // --- Load history ---
  async function loadHistory() {
    historyLoaded = true;
    const typingRow = showTyping();
    try {
      const resp = await fetch(historyUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: UID }),
      });
      typingRow.remove();

      if (resp.ok) {
        const data = await resp.json();
        const msgs = data.messages || [];
        if (msgs.length > 0) {
          let lastOffers = null;
          msgs.forEach(msg => {
            if (msg.role === 'user') {
              addMessage('user', msg.text, true);
            } else {
              addBotResponse({ text: msg.text, offers: msg.offers || [] }, true);
              if (msg.offers && msg.offers.length) lastOffers = msg.offers;
            }
          });
          if (lastOffers) updateCatalog(lastOffers);
          return;
        }
      }
    } catch (_) {
      typingRow.remove();
    }
    // Нет истории или ошибка — показываем приветствие
    addMessage('bot', ASSISTANT_GREETING);
  }

  // --- Parse answer ---
  function parseAnswer(raw) {
    if (raw == null) return null;
    if (typeof raw === 'object') return raw;
    if (typeof raw !== 'string') return String(raw);

    try { return JSON.parse(raw); } catch (_) {}
    try { return JSON.parse(raw.replace(/\\"/g, '"')); } catch (_) {}

    const result = {};
    const textMatch = raw.match(/"text"\s*:\s*"([\s\S]*?)(?:\\?",\s*"offers"|\\?"?\s*})/);
    if (textMatch) {
      result.text = textMatch[1]
        .replace(/\\n/g, '\n').replace(/\\t/g, '\t')
        .replace(/\\"/g, '"').replace(/\\\\/g, '\\');
    }

    // Ищем "offers" или "offers\" (ЛЛМ иногда экранирует закрывающую кавычку)
    const offersRe = /"offers\\"?/.exec(raw);
    const offersIdx = offersRe ? offersRe.index : -1;
    if (offersIdx !== -1) {
      const arrayStart = raw.indexOf('[', offersIdx);
      if (arrayStart !== -1) {
        let depth = 0, arrayEnd = -1;
        for (let i = arrayStart; i < raw.length; i++) {
          if (raw[i] === '[') depth++;
          else if (raw[i] === ']' && --depth === 0) { arrayEnd = i; break; }
        }
        if (arrayEnd !== -1) {
          const slice = raw.slice(arrayStart, arrayEnd + 1);
          // Fallback: раскрываем escape-последовательности (ЛЛМ мог экранировать все кавычки)
          const unescaped = slice.replace(/\\"/g, '"').replace(/\\n/g, '\n').replace(/\\t/g, '\t');
          try { result.offers = JSON.parse(slice); } catch (_) {
            try { result.offers = JSON.parse(unescaped); } catch (_) {}
          }
        }
      }
    }

    if (result.text !== undefined || result.offers) return result;
    return raw;
  }

  // --- Send ---
  async function sendMessage(text) {
    const sendBtn = document.getElementById('rag-send');
    const input = document.getElementById('rag-input');

    addMessage('user', text);
    input.value = '';
    input.style.height = 'auto';
    sendBtn.disabled = true;

    const typingRow = showTyping();

    try {
      const response = await fetch(askUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: UID, question: text })
      });

      typingRow.remove();

      if (!response.ok) {
        addMessage('bot', 'Ошибка сервера. Попробуйте позже.');
        return;
      }

      const data = await response.json();
      const parsed = parseAnswer(data.answer);
      if (parsed && typeof parsed === 'object') {
        addBotResponse(parsed);
      } else {
        addMessage('bot', parsed != null ? String(parsed) : 'Нет ответа.');
        updateCatalog([]);
      }
    } catch (e) {
      typingRow.remove();
      addMessage('bot', 'Не удалось подключиться к серверу.');
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  // --- Apply theme colors from data attributes ---
  function applyTheme() {
    const primary = currentScript.getAttribute('data-color-primary');
    const secondary = currentScript.getAttribute('data-color-secondary');
    if (!primary && !secondary) return;
    const el = document.getElementById('rag-widget');
    if (primary) el.style.setProperty('--rag-primary', primary);
    if (secondary) el.style.setProperty('--rag-secondary', secondary);
  }

  // --- Init ---
  function init() {
    buildWidget();
    applyTheme();

    const toggle = document.getElementById('rag-toggle');
    const win = document.getElementById('rag-window');
    const closeBtn = document.getElementById('rag-close-btn');
    const input = document.getElementById('rag-input');
    const sendBtn = document.getElementById('rag-send');
    const catalogCloseBtn = document.getElementById('rag-catalog-close');

    function openChat() {
      chatOpen = true;
      win.classList.add('rag-open');
      toggle.classList.add('rag-active');
      if (currentOffers.length) showCatalog();
      setTimeout(() => input.focus(), 300);
      if (!historyLoaded) loadHistory();
    }

    function closeChat() {
      chatOpen = false;
      win.classList.remove('rag-open');
      toggle.classList.remove('rag-active');
      hideCatalog();
    }

    toggle.addEventListener('click', () => chatOpen ? closeChat() : openChat());
    closeBtn.addEventListener('click', closeChat);
    catalogCloseBtn.addEventListener('click', hideCatalog);

    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        doSend();
      }
    });

    sendBtn.addEventListener('click', doSend);

    function doSend() {
      const text = input.value.trim();
      if (!text || sendBtn.disabled) return;
      sendMessage(text);
    }

    // Пересчитать каталог при изменении размера окна
    window.addEventListener('resize', () => {
      if (!chatOpen || !currentOffers.length) return;
      if (isLargeScreen()) showCatalog(); else hideCatalog();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
