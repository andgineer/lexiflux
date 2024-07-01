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
  text: string | null;
  updatedPanels: Set<string>;
} = {
  text: null,
  updatedPanels: new Set()
};

const dictionaryWindows: { [key: string]: Window | null } = {};

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
    selectedText: string,
    selectedWordSpans: HTMLElement[] | null = null,
  ): void {
  // if selectedWordSpans is null do not create translation span
  // if updateLexical is true, update the active lexical panel

  const encodedText = encodeURIComponent(selectedText);

  // todo: show "..loading.." in lexical panel if activePanelId is not null
  // for that we can rename getActiveLexicalArticleId to startLoadingInActivePanel
  const activePanelId = getActiveLexicalArticleId();

  if (!selectedWordSpans && (!activePanelId || currentSelection.updatedPanels.has(activePanelId))) {
    return;  // we already created translation span and updated the lexical panel or it is not opened
  }

  let urlParams = new URLSearchParams({
    'text': encodedText,
    'book-code': viewport.bookCode
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
        currentSelection.text = selectedText;
        if (translate) {
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
    let dictionaryWindow = window.open('', windowKey, windowFeatures);

    if (!dictionaryWindow) {
        console.error('Failed to open or focus window', windowKey);
        return;
    }

    const isNewWindow = dictionaryWindow.location.href === 'about:blank' || !dictionaryWindow.location.href.includes('/proxy.html');

    if (isNewWindow) {
        dictionaryWindow.location.href = `/proxy.html`;

        // Set up a listener for when the proxy is ready
        const proxyReadyListener = (event: MessageEvent) => {
            if (event.source === dictionaryWindow && event.data === 'PROXY_READY') {
                dictionaryWindow?.postMessage({ type: 'LOAD_URL', url: url }, '*');
                window.removeEventListener('message', proxyReadyListener);
            }
        };
        window.addEventListener('message', proxyReadyListener);
    } else {
        dictionaryWindow.postMessage({ type: 'LOAD_URL', url: url }, '*');
    }

    dictionaryWindow.focus();
}

function updateLexicalPanel(data: TranslationResponse, activePanelId: string): void {
  if (currentSelection.updatedPanels.has(activePanelId)) {
    return;
  }

  const panel = document.querySelector(`#${activePanelId}`) as HTMLElement;
  const windowKey = `Lexical-${activePanelId}`;

  if (data.url) {
    const url = data.url;
    const windowFeatures = 'width=800,height=600';

    if (data.window) {
      panel.innerHTML = `..see separate window.. <br><br><button id="openWindowButton-${activePanelId}" class="btn btn-primary btn-sm">Re-open</button>`;
      const openWindowButton = document.getElementById(`openWindowButton-${activePanelId}`);
      openWindowButton?.removeEventListener('click', () => handleOpenLexicalWindow(url, windowKey, windowFeatures));
      openWindowButton?.addEventListener('click', () => handleOpenLexicalWindow(url, windowKey, windowFeatures));
      openWindowButton?.click();
    } else {
      // Fetch the content from the URL and update the panel
      fetch(url)
        .then(response => response.text())
        .then(html => {
//           panel.innerHTML = html;
           let iframe = document.getElementById('lexical-frame-${activePanelId}') as HTMLIFrameElement | null;
           if (iframe) {
             iframe.src = html;
           }
        })
        .catch(error => {
          console.error('Error fetching content:', error);
          panel.innerHTML = 'Error loading content.';
        });
    }
  } else {
    // Put into the panel the article from backend
    panel.innerHTML = data.articles[lexicalArticleNumFromId(activePanelId)];
  }
  currentSelection.updatedPanels.add(activePanelId);
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
    if (currentSelection.text !== null) {
        sendTranslationRequest(currentSelection.text, null);
    }
}

function clearLexicalPanel(): void {
    currentSelection.text = null;
    currentSelection.updatedPanels.clear();

    const panelContent = document.getElementById('lexicalPanelContent');
    if (!panelContent) {
        console.error('Lexical panel content container is missing');
        return;
    }

    // Clear all tab panes
    const tabPanes = panelContent.querySelectorAll('.tab-pane');
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
