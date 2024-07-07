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
      if (currentNode.nodeType === Node.ELEMENT_NODE &&
          (currentNode as HTMLElement).classList.contains('word')) {
        const id = (currentNode as HTMLElement).id.replace('word-', '');
        if (id) wordIds.push(id);
      }
      if (currentNode === endNode) break;
      currentNode = getNextNode(currentNode);
    }
  }

  log('Selected word IDs:', wordIds);
  return wordIds;
}

function sendTranslationRequest(
    selectedRange: Range | null = null,
  ): void {
  // if selectedRange is null do not create translation span
  // if updateLexical is true, update the active lexical panel

  // todo: show "..loading.." in lexical panel if activePanelId is not null
  // for that we can rename getActiveLexicalArticleId to startLoadingInActivePanel
  const activePanelId = getActiveLexicalArticleId();

  if (!selectedRange && (!activePanelId || currentSelection.updatedPanels.has(activePanelId)) && currentSelection.wordIds === null) {
        return;
  }

  let wordIds = selectedRange ? getWordIdsFromRange(selectedRange) : currentSelection.wordIds;
  if (!wordIds || wordIds.length === 0) {
    console.log('No word IDs to translate');
    return;
  }

  let urlParams = new URLSearchParams({
    'word-ids': wordIds.join('.'),
    'book-code': viewport.bookCode,
    'book-page-number': viewport.pageNumber.toString(),
  });

  const translate = selectedRange !== null
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
        if (selectedRange) {
            createAndReplaceTranslationSpan(data.translatedText, selectedRange);
        }
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

function createAndReplaceTranslationSpan(translatedText: string, range: Range): void {
    const translationSpan = document.createElement('span');
    translationSpan.className = 'translation-span';

    const translationDiv = document.createElement('div');
    translationDiv.className = 'translation-text';
    translationDiv.textContent = translatedText;

    translationSpan.appendChild(translationDiv);

    // Adjust the range to include full words
    let startNode: Node | null = range.startContainer;
    let endNode: Node | null = range.endContainer;

    // Adjust start node
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

    // Adjust end node
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
        range.setStartBefore(startNode);
        range.setEndAfter(endNode);
    }

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

    ensureVisible(translationSpan);
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
