// translate.ts
import { log } from './utils'; // Assuming log function is used here
import { viewport } from './viewport'; // If viewport functionalities are required

interface TranslationResponse {
  translatedText: string;
  articles: { [key: string]: string };
  url: string | null;
  window: boolean | null;
}

let currentSelection: {
  wordIds: string[] | null;
  updatedPanels: Set<string>;
} = {
  wordIds: null,
  updatedPanels: new Set()
};

let dictionaryWindows: { [key: string]: Window | null } = {};

function getActiveLexicalArticleId(): string | null {
  const infoPanel = document.getElementById('lexical-panel');
  const isInfoPanelVisible = infoPanel ? infoPanel.classList.contains('show') : false;

  if (!isInfoPanelVisible) {
    return null;
  }

  const activeTabContent = document.querySelector('#lexicalPanelContent .tab-pane.active') as HTMLElement | null;
  return activeTabContent ? activeTabContent.id : null;
}


function lexicalArticleNumFromId(id: string | null): string {
  // from lexical article div ID get the number of the article
  if (!id) return '';
  const match = id.match(/-(\d+)$/);
  return match ? match[1] : '';
}

function sendTranslationRequest(
    wordIds: string[],
    selectedWordSpans: HTMLElement[] | null = null,
  ): void {
  // if selectedWordSpans is null do not create translation span
  // if updateLexical is true, update the active lexical panel

  // todo: show "..loading.." in lexical panel if activePanelId is not null
  // for that we can rename getActiveLexicalArticleId to startLoadingInActivePanel
  const activePanelId = getActiveLexicalArticleId();

  if (!selectedWordSpans && (!activePanelId || currentSelection.updatedPanels.has(activePanelId))) {
    return;  // we already created translation span and updated the lexical panel or it is not opened
  }

  let urlParams = new URLSearchParams({
    'word-ids': wordIds.join('.'),
    'book-code': viewport.bookCode,
    'book-page-number': viewport.pageNumber.toString(),
  });

  const translate = selectedWordSpans !== null
  if (!translate) {
    urlParams.append('translate', 'false');
  }

  const lexicalArticle = lexicalArticleNumFromId(activePanelId);
  if (lexicalArticle) {
    urlParams.append('lexical-article', lexicalArticle);
  }

  const url = `/translate?${urlParams.toString()}`;

  fetch(url)
    .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
    .then((data: TranslationResponse) => {
        log('Translated:', data);
        currentSelection.wordIds = wordIds;
        if (translate) {
            let selectedText = selectedWordSpans.map(span => span.textContent).join(' ');
            createAndReplaceTranslationSpan(selectedText, data.translatedText, selectedWordSpans);
        };
        if (activePanelId) {
            updateLexicalPanel(data, activePanelId);
        }
    })
    .catch(error => {
      console.error('Error during translation:', error);
    });
}

function handleOpenLexicalWindow(url: string, windowKey: string, windowFeatures: string): void {
    let dictionaryWindow = dictionaryWindows[windowKey];

    if (dictionaryWindow && !dictionaryWindow.closed) {
        dictionaryWindow.location.href = url;
    } else {
        dictionaryWindow = window.open(url, windowKey, windowFeatures);
        dictionaryWindows[windowKey] = dictionaryWindow;
    }
    if (dictionaryWindow) {
        dictionaryWindow.focus();
    }
}

function updateLexicalPanel(data: TranslationResponse, activePanelId: string): void {
  // activePanelId - num of the lexical article
  let articleId = lexicalArticleNumFromId(activePanelId);

  console.log('updateLexicalPanel', data, activePanelId, articleId);
  if (currentSelection.updatedPanels.has(articleId)) {
    return;
  }

  console.log(`lexical-content-${articleId}`, `lexical-frame-${articleId}`)
  const contentDiv = document.getElementById(`lexical-content-${articleId}`) as HTMLElement;
  const iframe = document.getElementById(`lexical-frame-${articleId}`) as HTMLIFrameElement;
  const windowKey = `Lexical-${articleId}`;
  console.log(contentDiv, iframe, windowKey);

  // Show spinner
  contentDiv.innerHTML = `
    <div class="spinner-border text-primary" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  `;

  if (data.url) {
    const url = data.url;
    const windowFeatures = 'location=no,menubar=no,toolbar=no,scrollbars=yes,width=800,height=600';  // todo: width from window

    if (data.window) {
      // Hide spinner and show button
      contentDiv.innerHTML = `
        ..see separate window.. <br><br>
        <button id="openWindowButton-${articleId}" class="btn btn-primary btn-sm">Open in new window</button>
      `;
      const openWindowButton = document.getElementById(`openWindowButton-${articleId}`);
      openWindowButton?.removeEventListener('click', () => handleOpenLexicalWindow(url, windowKey, windowFeatures));
      openWindowButton?.addEventListener('click', () => handleOpenLexicalWindow(url, windowKey, windowFeatures));
      openWindowButton?.click();
    } else {
      // Load URL in iframe
      contentDiv.innerHTML = ''; // Hide spinner
      iframe.src = url;
      iframe.style.display = 'block';
    }
  } else {
    // Load article content
    contentDiv.innerHTML = data.articles[articleId];
    iframe.style.display = 'none';
  }

  currentSelection.updatedPanels.add(articleId);
}

function ensureVisible(element: HTMLSpanElement): void {
    // if the element is not visible, scroll to it
    if (element.getBoundingClientRect().bottom > viewport.bookPageScroller.getBoundingClientRect().bottom) {
        viewport.bookPageScroller.scrollTop += element.getBoundingClientRect().bottom - viewport.bookPageScroller.getBoundingClientRect().bottom;
    }
}

function createAndReplaceTranslationSpan(selectedText: string, translatedText: string, selectedWordSpans: HTMLElement[]): void {
    let firstWordSpan = selectedWordSpans[0];
    let translationSpan = document.createElement('span');
    translationSpan.dataset.originalHtml = selectedWordSpans.map(span => span.outerHTML).join('');
    translationSpan.className = 'translation-span';
    translationSpan.id = 'translation-' + firstWordSpan.id;

    let translationDiv = document.createElement('div');
    translationDiv.className = 'translation-text';
    translationDiv.textContent = translatedText;

    let textDiv = document.createElement('div');
    textDiv.className = 'text';
    // Update to include original HTML instead of just text
    textDiv.innerHTML = selectedWordSpans.map(span => span.outerHTML).join('&nbsp;');

    translationSpan.appendChild(translationDiv);
    translationSpan.appendChild(textDiv);
    viewport.getWordsContainer().insertBefore(translationSpan, firstWordSpan);

    // Remove the original word spans
    selectedWordSpans.forEach(span => {
        viewport.getWordsContainer().removeChild(span);
    });
    ensureVisible(translationSpan);
}

function lexicalPanelSwitched(tabId: string): void {
    if (currentSelection.wordIds !== null) {
        sendTranslationRequest(currentSelection.wordIds, null);
    }
}

function clearLexicalPanel(): void {
    currentSelection.wordIds = null;
    currentSelection.updatedPanels.clear();

    const panelContent = document.getElementById('lexicalPanelContent');
    if (!panelContent) {
        console.error('Lexical panel content container is missing');
        return;
    }

    // Clear all tab panes
    const tabPanes = panelContent.querySelectorAll('.lexical-content');
    tabPanes.forEach((pane) => {
        pane.innerHTML = '';
    });

    // If there are any iframes, reset their src
    const iframes = panelContent.querySelectorAll('iframe');
    iframes.forEach((iframe) => {
        iframe.src = '';
    });
}

export { sendTranslationRequest, createAndReplaceTranslationSpan, TranslationResponse, lexicalPanelSwitched, clearLexicalPanel };
