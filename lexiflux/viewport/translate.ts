import { log } from './utils';
import { viewport } from './viewport';
import { spanManager, TranslationSpan } from './TranslationSpanManager';


interface TranslationResponse {
  article?: string;
  url?: string | null;
  window?: boolean | null;
}

let currentSelection: {
  wordIds: number[] | null;
  updatedPanels: Set<string>;
} = {
  wordIds: null,
  updatedPanels: new Set()
};

let dictionaryWindows: { [key: string]: Window | null } = {};

function sendTranslationRequest(selectedRange: Range | null = null): void {
  const activePanelId = getActiveLexicalArticleId();
  const initialWordIds = getWordIds(selectedRange);

  if (!shouldSendRequest(selectedRange, activePanelId, initialWordIds)) {
    return;
  }

  if (initialWordIds === null || initialWordIds.length === 0) {
    console.log('No word IDs to translate');
    return;
  }

  // Get extended word IDs
  const extendedWordIds = Array.from(spanManager.getExtendedWordIds(initialWordIds)).sort((a, b) => a - b);

  // Only handle translation spans if there's a new selection
  if (selectedRange) {
    const spansToRemove = spanManager.getAffectedSpans(initialWordIds);
    spansToRemove.forEach(spanId => {
      const span = document.getElementById(`translation-word-${spanId}`);
      if (span) {
        hideTranslation(span as HTMLElement);
      }
    });

    handleInTextTranslation(selectedRange, extendedWordIds);
  }

  currentSelection.wordIds = extendedWordIds;

  if (activePanelId) {
    const lexicalArticle = lexicalArticleNumFromId(activePanelId);
    if (lexicalArticle && !currentSelection.updatedPanels.has(lexicalArticle)) {
      handleLexicalArticleUpdate(activePanelId, extendedWordIds);
    }
  }
}

function getWordIds(selectedRange: Range | null): number[] | null {
  return selectedRange ? getWordIdsFromRange(selectedRange) : currentSelection.wordIds;
}

function shouldSendRequest(selectedRange: Range | null, activePanelId: string | null, wordIds: number[] | null): boolean {
  if (!selectedRange && (!activePanelId || currentSelection.updatedPanels.has(activePanelId)) && currentSelection.wordIds === null) {
    return false;
  }
  if (!wordIds || wordIds.length === 0) {
    return false;
  }
  return true;
}

function handleInTextTranslation(selectedRange: Range, wordIds: number[]): void {
  // Create new translation span
  const firstWordId = wordIds[0];
  const lastWordId = wordIds[wordIds.length - 1];
  const extendedRange = createRangeFromWords(firstWordId, lastWordId);
  const translationSpan = createTranslationSpanWithSpinner(extendedRange);
  const params = createRequestParams(wordIds, '0');

  makeRequest(params)
    .then(result => {
      if (result) {
        updateTranslationSpan(result.data, translationSpan);
        // Update span manager
        spanManager.addSpan(firstWordId, lastWordId);
      } else {
        showErrorInTranslationSpan(translationSpan);
      }
    })
    .catch(() => {
      showErrorInTranslationSpan(translationSpan);
    });
}

function createRangeFromWords(firstWordId: number, lastWordId: number): Range {
  const container = document.getElementById('words-container');
  if (!container) throw new Error('Words container not found');

  const firstWord = document.getElementById(`word-${firstWordId}`);
  const lastWord = document.getElementById(`word-${lastWordId}`);

  if (!firstWord || !lastWord) throw new Error('First or last word not found');

  const range = document.createRange();
  range.setStart(firstWord, 0);
  range.setEnd(lastWord, lastWord.childNodes.length);
  return range;
}

function handleLexicalArticleUpdate(activePanelId: string, wordIds: number[]): void {
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

function createRequestParams(wordIds: number[], lexicalArticle: string): URLSearchParams {
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

  if (currentNode instanceof HTMLElement) {
    if (currentNode.classList.contains('word')) {
      return currentNode;
    }
    const selector = direction === 'forward' ? '.word' : '.word:last-child';
    const closestWord = currentNode.querySelector(selector);
    return closestWord || currentNode;
  }

  return currentNode || node;
}

function adjustRangeToWholeWords(range: Range): void {
  const startNode = adjustNodeToNearestWord(range.startContainer, 'forward');
  const endNode = adjustNodeToNearestWord(range.endContainer, 'backward');

  if (startNode instanceof HTMLElement) {
    range.setStartBefore(startNode);
  } else if (startNode.nodeType === Node.TEXT_NODE) {
    range.setStart(startNode, 0);
  }

  if (endNode instanceof HTMLElement) {
    range.setEndAfter(endNode);
  } else if (endNode.nodeType === Node.TEXT_NODE) {
    range.setEnd(endNode, endNode.textContent?.length || 0);
  }
}

function getWordIdsFromRange(range: Range): number[] {
  const container = document.getElementById('words-container');
  if (!container) return [];

  const wordIds: number[] = [];
  let currentNode: Node | null = range.startContainer;

  // Check if the range starts inside a word
  if (currentNode.nodeType === Node.TEXT_NODE && currentNode.parentNode &&
      (currentNode.parentNode as HTMLElement).classList.contains('word')) {
    currentNode = currentNode.parentNode;
  }

  // Include the first word if it's partially selected
  if (currentNode.nodeType === Node.ELEMENT_NODE &&
      (currentNode as HTMLElement).classList.contains('word')) {
    const id = (currentNode as HTMLElement).id.replace('word-', '');
    wordIds.push(parseInt(id, 10));
  }

  // Move to the next node if we're not already at the end
  if (currentNode !== range.endContainer) {
    currentNode = getNextNode(currentNode);
  }

  while (currentNode && container.contains(currentNode)) {
    if (currentNode.nodeType === Node.ELEMENT_NODE &&
        (currentNode as HTMLElement).classList.contains('word')) {
      const id = (currentNode as HTMLElement).id.replace('word-', '');
      wordIds.push(parseInt(id, 10));
    }

    if (currentNode === range.endContainer) break;
    currentNode = getNextNode(currentNode);
  }

  return wordIds;
}

function createTranslationSpanWithSpinner(range: Range): HTMLSpanElement {
  const translationSpan = document.createElement('span');
  translationSpan.className = 'translation-span d-inline-block position-relative';

  const spinnerDiv = document.createElement('div');
  spinnerDiv.className = 'd-flex justify-content-center align-items-center';
  spinnerDiv.innerHTML = `
    <div class="spinner-border spinner-border-sm text-primary" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  `;

  const translationTextDiv = document.createElement('div');
  translationTextDiv.className = 'translation-text text-center text-muted small mb-1';

  const originalTextDiv = document.createElement('div');
  originalTextDiv.className = 'original-text bg-light p-1 rounded';

  translationSpan.appendChild(spinnerDiv);
  translationSpan.appendChild(translationTextDiv);
  translationSpan.appendChild(originalTextDiv);

  // Adjust the range to include only selected words
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

  // Create a new range for the original text and select it
  const selection = window.getSelection();
  if (selection) {
    const newRange = document.createRange();
    // Select all content within the originalTextDiv
    newRange.selectNodeContents(originalTextDiv);
    selection.removeAllRanges();
    selection.addRange(newRange);
  }

  viewport.adjustTopTranslationSpans();
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
  const spanId = parseInt(translationSpan.id.replace('translation-word-', ''), 10);
  spanManager.removeSpan(spanId);

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
  const spinnerDiv = translationSpan.querySelector('div:first-child');
  if (spinnerDiv) {
    spinnerDiv.remove();
  }

  const translationTextDiv = translationSpan.querySelector('.translation-text') as HTMLElement;
  if (translationTextDiv) {
    translationTextDiv.className = 'alert alert-danger p-1 mb-1 d-flex align-items-center';
    translationTextDiv.setAttribute('role', 'alert');
    translationTextDiv.innerHTML = `
      <span class="me-2" aria-hidden="true">⚠️</span>
      <div>Translation failed</div>
    `;
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
        <button id="openWindowButton-${articleId}" class="btn btn-primary btn-sm">Open in separate window</button>
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

function openDictionaryWindow(url: string, windowKey: string, windowFeatures: string): Window | null {
  const newWindow = window.open(url, windowKey, windowFeatures);
  dictionaryWindows[windowKey] = newWindow;
  return newWindow;
}

function handleOpenLexicalWindow(url: string, windowKey: string, windowFeatures: string): void {
  let dictionaryWindow = dictionaryWindows[windowKey];
  if (!dictionaryWindow || dictionaryWindow.closed) {
    // The window is closed or does not exist, open a new one
    dictionaryWindow = openDictionaryWindow(url, windowKey, windowFeatures);
  } else {
    // The window is already open. Just change its URL and bring it into focus.
    try {
      dictionaryWindow.location.href = url;
      dictionaryWindow.focus();
    } catch (error) {
      // If changing the URL or focusing triggers an error, re-open the window.
      openDictionaryWindow(url, windowKey, windowFeatures);
    }
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
  // Only send translation request if we have word IDs but haven't updated this panel yet
  if (currentSelection.wordIds !== null) {
    const lexicalArticle = lexicalArticleNumFromId(tabId);
    if (lexicalArticle && !currentSelection.updatedPanels.has(lexicalArticle)) {
      sendTranslationRequest(null);
    }
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