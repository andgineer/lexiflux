// translate.ts
import { log } from './utils'; // Assuming log function is used here
import { viewport } from './viewport'; // If viewport functionalities are required

interface TranslationResponse {
  translatedText: string;
  articles: { [key: string]: string };
}

let currentSelection: {
  text: string | null;
  updatedPanels: Set<string>;
} = {
  text: null,
  updatedPanels: new Set()
};

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

function updateLexicalPanel(data: TranslationResponse, activePanelId: string): void {
  if (currentSelection.updatedPanels.has(activePanelId)) {
    return;
  }
  const panel = document.querySelector(`#${activePanelId}`) as HTMLElement;
  panel.innerHTML = data.articles[lexicalArticleNumFromId(activePanelId)];
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
    // todo: for loop to clear all panels
    currentSelection.text = null;
    currentSelection.updatedPanels.clear();
    const dictionaryPanel = document.getElementById('dictionary-panel-1');
    const explainPanel = document.getElementById('explain-panel');
    const examplesPanel = document.getElementById('examples-panel');

    if (!dictionaryPanel || !explainPanel || !examplesPanel) {
        log('One of the translation panels is missing');
        return;
    }
    dictionaryPanel.innerHTML = '';
    explainPanel.innerHTML = '';
    examplesPanel.innerHTML = '';
}

export { sendTranslationRequest, createAndReplaceTranslationSpan, TranslationResponse, lexicalPanelSwitched, clearLexicalPanel };
