import { log } from './utils';
import { viewport } from './viewport';

interface TranslationResponse {
  article?: string;
  url?: string | null;
  window?: boolean | null;
}

let currentSelection: {
  wordIds: string[] | null;
  updatedPanels: Set<string>;
} = {
  wordIds: null,
  updatedPanels: new Set()
};

let dictionaryWindows: { [key: string]: Window | null } = {};

function sendTranslationRequest(selectedRange: Range | null = null): void {
  const activePanelId = getActiveLexicalArticleId();
  const wordIds = getWordIds(selectedRange);

  if (!shouldSendRequest(selectedRange, activePanelId, wordIds)) {
    return;
  }

  if (wordIds === null) {
    console.log('No word IDs to translate');
    return;
  }

  currentSelection.wordIds = wordIds;

  if (selectedRange) {
    handleInTextTranslation(selectedRange, wordIds);
  }

  if (activePanelId) {
    const lexicalArticle = lexicalArticleNumFromId(activePanelId);
    if (lexicalArticle && !currentSelection.updatedPanels.has(lexicalArticle)) {
      handleLexicalArticleUpdate(activePanelId, wordIds);
    }
  }
}

function getWordIds(selectedRange: Range | null): string[] | null {
  return selectedRange ? getWordIdsFromRange(selectedRange) : currentSelection.wordIds;
}

function shouldSendRequest(selectedRange: Range | null, activePanelId: string | null, wordIds: string[] | null): boolean {
  if (!selectedRange && (!activePanelId || currentSelection.updatedPanels.has(activePanelId)) && currentSelection.wordIds === null) {
    return false;
  }
  if (!wordIds || wordIds.length === 0) {
    return false;
  }
  return true;
}

function handleInTextTranslation(selectedRange: Range, wordIds: string[]): void {
  const translationSpan = createTranslationSpanWithSpinner(selectedRange);
  const params = createRequestParams(wordIds, '0');

  makeRequest(params)
    .then(result => {
      if (result) {
        updateTranslationSpan(result.data, translationSpan);
      } else {
        showErrorInTranslationSpan(translationSpan);
      }
    })
    .catch(() => {
      showErrorInTranslationSpan(translationSpan);
    });
}

function handleLexicalArticleUpdate(activePanelId: string, wordIds: string[]): void {
  const lexicalArticle = lexicalArticleNumFromId(activePanelId);
  if (lexicalArticle) {
    if (currentSelection.updatedPanels.has(lexicalArticle)) {
      return;
    }
    showSpinnerInLexicalPanel(lexicalArticle);
    const params = createRequestParams(wordIds, lexicalArticle);

    makeRequest(params)
      .then(result => {
        if (result) {
          updateLexicalPanel(result.data, activePanelId);
        } else {
          showErrorInLexicalPanel(lexicalArticle);
        }
      })
      .catch((error) => {
        console.error('Error in handleLexicalArticleUpdate:', error);
        showErrorInLexicalPanel(lexicalArticle);
      });
  }
}

function createRequestParams(wordIds: string[], lexicalArticle: string): URLSearchParams {
  const params = new URLSearchParams({
    'word-ids': wordIds.join('.'),
    'book-code': viewport.bookCode,
    'book-page-number': viewport.pageNumber.toString(),
    'lexical-article': lexicalArticle,
  });

  return params;
}

function makeRequest(params: URLSearchParams): Promise<{ data: TranslationResponse; } | undefined> {
  const url = `/translate?${params.toString()}`;
  return fetch(url)
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    })
    .then((data: TranslationResponse) => {
      return { data };
    })
    .catch(error => {
      console.error('Error during translation:', error);
      throw error;
    });
}


function adjustNodeToNearestWord(node: Node, direction: 'forward' | 'backward'): Node {
  let currentNode: Node | null = node;

  while (currentNode && currentNode.nodeType === Node.TEXT_NODE) {
    const siblingProp = direction === 'forward' ? 'nextSibling' : 'previousSibling';
    const sibling = currentNode[siblingProp];

    if (sibling && sibling.nodeType === Node.ELEMENT_NODE &&
        (sibling as HTMLElement).classList.contains('word')) {
      return sibling;
    }
    currentNode = currentNode.parentNode;
  }

  if (currentNode instanceof HTMLElement && !currentNode.classList.contains('word')) {
    const selector = direction === 'forward' ? '.word' : '.word:last-child';
    const closestWord = direction === 'forward'
      ? currentNode.querySelector(selector)
      : currentNode.querySelectorAll(selector)[0];
    return closestWord || currentNode;
  }

  return currentNode || node;
}

function adjustRangeToWholeWords(range: Range): void {
  const startNode = adjustNodeToNearestWord(range.startContainer, 'forward');
  const endNode = adjustNodeToNearestWord(range.endContainer, 'backward');

  if (startNode instanceof HTMLElement) {
    range.setStartBefore(startNode);
  }
  if (endNode instanceof HTMLElement) {
    range.setEndAfter(endNode);
  }
}

function getWordIdsFromRange(range: Range): string[] {
  const container = document.getElementById('words-container');
  if (!container) return [];

  const wordIds: string[] = [];
  const startNode = adjustNodeToNearestWord(range.startContainer, 'forward');
  const endNode = adjustNodeToNearestWord(range.endContainer, 'backward');

  if (startNode && endNode) {
    let currentNode: Node | null = startNode;
    while (currentNode) {
      if (currentNode.nodeType === Node.ELEMENT_NODE &&
          (currentNode as HTMLElement).classList.contains('word')) {
        const id = (currentNode as HTMLElement).id.replace('word-', '');
        if (id) wordIds.push(id);
      }
      if (currentNode === endNode) break;
      currentNode = getNextNode(currentNode);
    }
  }

  return wordIds;
}

function createTranslationSpanWithSpinner(range: Range): HTMLSpanElement {
  const translationSpan = document.createElement('span');
  translationSpan.className = 'translation-span d-inline-block position-relative';

  const spinnerDiv = document.createElement('div');
  spinnerDiv.className = 'spinner-border text-primary position-absolute top-0 start-50 translate-middle-x';
  spinnerDiv.innerHTML = '<span class="visually-hidden">Loading...</span>';

  const translationTextDiv = document.createElement('div');
  translationTextDiv.className = 'translation-text text-center text-muted small mb-1';

  const originalTextDiv = document.createElement('div');
  originalTextDiv.className = 'original-text bg-light p-1 rounded';

  translationSpan.appendChild(spinnerDiv);
  translationSpan.appendChild(translationTextDiv);
  translationSpan.appendChild(originalTextDiv);

  // Adjust the range to include full words
  adjustRangeToWholeWords(range);

  // Clone the contents of the adjusted range
  const contents = range.cloneContents();
  originalTextDiv.appendChild(contents);

  // Replace the range contents with the translation span
  range.deleteContents();
  range.insertNode(translationSpan);

  // Assign a unique ID to the translation span
  const firstWordSpan = originalTextDiv.querySelector('.word');
  if (firstWordSpan) {
    translationSpan.id = 'translation-' + firstWordSpan.id;
  }

  return translationSpan;
}

function updateTranslationSpan(data: TranslationResponse, translationSpan: HTMLSpanElement): void {
  // Remove the spinner
  const spinner = translationSpan.querySelector('.spinner-border');
  if (spinner) {
    spinner.remove();
  }

  const translationTextDiv = translationSpan.querySelector('.translation-text') as HTMLElement;
  const originalTextDiv = translationSpan.querySelector('.original-text') as HTMLElement;

  if (data.article) {
    translationTextDiv.textContent = data.article;

    // Adjust width and wrapping
    adjustTranslationWidth(translationSpan, translationTextDiv, originalTextDiv);
  } else {
    showErrorInTranslationSpan(translationSpan);
  }

  ensureVisible(translationSpan);
}

function adjustTranslationWidth(translationSpan: HTMLSpanElement, translationTextDiv: HTMLElement, originalTextDiv: HTMLElement): void {
  const maxWidth = viewport.bookPageScroller.offsetWidth - 40; // 20px padding on each side
  const buffer = 10; // Add a small buffer to prevent unnecessary wrapping

  const originalWidth = originalTextDiv.offsetWidth + buffer;
  const translationWidth = translationTextDiv.offsetWidth + buffer;

  translationSpan.style.maxWidth = `${maxWidth}px`;
  translationSpan.style.display = 'inline-block';

  if (translationWidth <= originalWidth) {
    // Translation fits within original text width
    translationSpan.style.width = `${originalWidth}px`;
  } else {
    // Translation is wider than original text
    translationSpan.style.width = `${Math.min(translationWidth, maxWidth)}px`;
    translationTextDiv.style.whiteSpace = 'normal';
    originalTextDiv.style.whiteSpace = 'normal';
    originalTextDiv.style.overflowX = 'visible';
  }

  // Ensure the original text is below the translation
  originalTextDiv.style.display = 'block';
  originalTextDiv.style.marginTop = '5px';
}

function hideTranslation(translationSpan: HTMLElement): void {
  const parent = translationSpan.parentNode;
  if (parent) {
    const originalTextDiv = translationSpan.querySelector('.original-text');
    if (originalTextDiv) {
      // Move all child nodes of the original text div to the parent
      while (originalTextDiv.firstChild) {
        parent.insertBefore(originalTextDiv.firstChild, translationSpan);
      }
    }
    // Remove the translation span
    translationSpan.remove();
  }
}

function showErrorInTranslationSpan(translationSpan: HTMLSpanElement): void {
  const translationTextDiv = translationSpan.querySelector('.translation-text') as HTMLElement;
  if (translationTextDiv) {
    translationTextDiv.className = 'translation-text text-danger small mb-1';
    translationTextDiv.textContent = 'Translation failed.';
  }
}

function showErrorInLexicalPanel(articleId: string): void {
  const contentDiv = document.getElementById(`lexical-content-${articleId}`) as HTMLElement;
  if (contentDiv) {
    contentDiv.innerHTML = `
      <div class="alert alert-danger" role="alert">
        Failed to load lexical article. Please try again.
      </div>
    `;
  }
}

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

function getNextNode(node: Node): Node | null {
  if (node.firstChild) {
    return node.firstChild;
  }
  while (node) {
    if (node.nextSibling) {
      return node.nextSibling;
    }
    node = node.parentNode as Node;
  }
  return null;
}

function updateLexicalPanel(data: TranslationResponse, activePanelId: string): void {
  // activePanelId - num of the lexical article
  let articleId = lexicalArticleNumFromId(activePanelId);


  if (currentSelection.updatedPanels.has(articleId)) {
    return;
  }

  const contentDiv = document.getElementById(`lexical-content-${articleId}`) as HTMLElement;
  const iframe = document.getElementById(`lexical-frame-${articleId}`) as HTMLIFrameElement;
  const windowKey = `Lexical-${articleId}`;

  // Show spinner
  contentDiv.innerHTML = `
    <div class="spinner-border text-primary" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  `;

  if (data.url) {
    // Handle Site type article
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
  } else if (data.article) {
    contentDiv.innerHTML = data.article;
    iframe.style.display = 'none';
  } else {
    // Handle error case
    contentDiv.innerHTML = `
      <div class="alert alert-danger" role="alert">
        Failed to load lexical article. Please try again.
      </div>
    `;
  }

  currentSelection.updatedPanels.add(articleId);
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

function ensureVisible(element: HTMLSpanElement): void {
  if (element.getBoundingClientRect().bottom > viewport.bookPageScroller.getBoundingClientRect().bottom) {
    viewport.bookPageScroller.scrollTop += element.getBoundingClientRect().bottom - viewport.bookPageScroller.getBoundingClientRect().bottom;
  }
}

function showSpinnerInLexicalPanel(articleId: string): void {
  const contentDiv = document.getElementById(`lexical-content-${articleId}`) as HTMLElement;
  if (contentDiv) {
    contentDiv.innerHTML = `
      <div class="d-flex flex-column align-items-center">
        <div class="spinner-border text-primary mb-3" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <p class="text-center text-muted">
          <small>Generating AI response. This may take a moment...</small>
        </p>
      </div>
    `;
  }
}

function lexicalPanelSwitched(tabId: string): void {
  if (currentSelection.wordIds !== null) {
    sendTranslationRequest(null);
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

  const tabPanes = panelContent.querySelectorAll('.lexical-content');
  tabPanes.forEach((pane) => {
    pane.innerHTML = '';
  });

  const iframes = panelContent.querySelectorAll('iframe');
  iframes.forEach((iframe) => {
    iframe.src = '';
  });
}

export { sendTranslationRequest, TranslationResponse, lexicalPanelSwitched, clearLexicalPanel, hideTranslation };