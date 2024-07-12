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

function createTranslationSpanWithSpinner(range: Range): HTMLSpanElement {
  const translationSpan = document.createElement('span');
  translationSpan.className = 'translation-span';

  const spinnerDiv = document.createElement('div');
  spinnerDiv.className = 'spinner-border text-primary';
  spinnerDiv.innerHTML = '<span class="visually-hidden">Loading...</span>';

  translationSpan.appendChild(spinnerDiv);

  // Adjust the range to include full words
  adjustRangeToWholeWords(range);

  // Clone the contents of the adjusted range
  const contents = range.cloneContents();
  translationSpan.appendChild(contents);

  // Replace the range contents with the translation span
  range.deleteContents();
  range.insertNode(translationSpan);

  // Assign a unique ID to the translation span
  const firstWordSpan = translationSpan.querySelector('.word');
  if (firstWordSpan) {
    translationSpan.id = 'translation-' + firstWordSpan.id;
  }

  return translationSpan;
}

function adjustRangeToWholeWords(range: Range): void {
  let startNode: Node | null = range.startContainer;
  let endNode: Node | null = range.endContainer;

  // Adjust start node
  if (startNode.nodeType === Node.TEXT_NODE && startNode.parentNode) {
    if ((startNode.parentNode as HTMLElement).classList.contains('word')) {
      range.setStartBefore(startNode.parentNode);
    } else {
      // Find the first word node after the start of the selection
      let nextNode = startNode.nextSibling;
      while (nextNode && !(nextNode instanceof HTMLElement && nextNode.classList.contains('word'))) {
        nextNode = nextNode.nextSibling;
      }
      if (nextNode) {
        range.setStartBefore(nextNode);
      }
    }
  } else if (startNode instanceof HTMLElement && !startNode.classList.contains('word')) {
    // Find the first word node within or after the start of the selection
    const firstWord = startNode.querySelector('.word');
    if (firstWord) {
      range.setStartBefore(firstWord);
    }
  }

  // Adjust end node
  if (endNode.nodeType === Node.TEXT_NODE && endNode.parentNode) {
    if ((endNode.parentNode as HTMLElement).classList.contains('word')) {
      range.setEndAfter(endNode.parentNode);
    } else {
      // Find the last word node before the end of the selection
      let previousNode = endNode.previousSibling;
      while (previousNode && !(previousNode instanceof HTMLElement && previousNode.classList.contains('word'))) {
        previousNode = previousNode.previousSibling;
      }
      if (previousNode) {
        range.setEndAfter(previousNode);
      }
    }
  } else if (endNode instanceof HTMLElement && !endNode.classList.contains('word')) {
    // Find the last word node within or before the end of the selection
    const words = endNode.querySelectorAll('.word');
    if (words.length > 0) {
      range.setEndAfter(words[words.length - 1]);
    }
  }
}

function updateTranslationSpan(data: TranslationResponse, translationSpan: HTMLSpanElement): void {
  // Remove the spinner
  const spinner = translationSpan.querySelector('.spinner-border');
  if (spinner) {
    spinner.remove();
  }

  // Create and insert the translation text div
  // todo: support also Site response? How to show inlined?
  if (data.article) {
      const translationDiv = document.createElement('div');
      translationDiv.className = 'translation-text';
      translationDiv.textContent = data.article;
      translationSpan.insertBefore(translationDiv, translationSpan.firstChild);
  } else {
    showErrorInTranslationSpan(translationSpan);
  }
  ensureVisible(translationSpan);
}

function showErrorInTranslationSpan(translationSpan: HTMLSpanElement): void {
  // Remove the spinner
  const spinner = translationSpan.querySelector('.spinner-border');
  if (spinner) {
    spinner.remove();
  }

  // Add error message
  const errorDiv = document.createElement('div');
  errorDiv.className = 'translation-error';
  errorDiv.textContent = 'Translation failed. Please try again.';
  translationSpan.insertBefore(errorDiv, translationSpan.firstChild);
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

function getWordIdsFromRange(range: Range): string[] {
  const container = document.getElementById('words-container');
  if (!container) return [];

  const wordIds: string[] = [];
  let startNode: Node | null = range.startContainer;
  let endNode: Node | null = range.endContainer;

  // Adjust start node to include the whole word
  while (startNode && startNode.nodeType === Node.TEXT_NODE) {
    if (startNode.previousSibling && startNode.previousSibling.nodeType === Node.ELEMENT_NODE &&
        (startNode.previousSibling as HTMLElement).classList.contains('word')) {
      startNode = startNode.previousSibling;
      break;
    }
    startNode = startNode.parentNode;
  }
  if (startNode instanceof HTMLElement && !startNode.classList.contains('word')) {
    const closestWord = startNode.querySelector('.word');
    startNode = closestWord || startNode;
  }

  // Adjust end node to include the whole word
  while (endNode && endNode.nodeType === Node.TEXT_NODE) {
    if (endNode.nextSibling && endNode.nextSibling.nodeType === Node.ELEMENT_NODE &&
        (endNode.nextSibling as HTMLElement).classList.contains('word')) {
      endNode = endNode.nextSibling;
      break;
    }
    endNode = endNode.parentNode;
  }
  if (endNode instanceof HTMLElement && !endNode.classList.contains('word')) {
    const words = endNode.querySelectorAll('.word');
    endNode = words[words.length - 1] || endNode;
  }

  if (startNode && endNode) {
    let currentNode: Node | null = startNode;
    while (currentNode) {
      // todo: replace with select by class
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
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
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

export { sendTranslationRequest, TranslationResponse, lexicalPanelSwitched, clearLexicalPanel };