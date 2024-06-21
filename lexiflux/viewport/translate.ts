// translate.ts
import { log } from './utils'; // Assuming log function is used here
import { viewport } from './viewport'; // If viewport functionalities are required

interface TranslationResponse {
  translatedText: string;
  article: string;
}

let currentSelection = {
  text: '',
  updatedPanels: new Set()
};

function sendTranslationRequest(
    selectedText: string,
    selectedWordSpans: HTMLElement[] | null = null,
    updateLexical = false,
  ): void {
  // if selectedWordSpans is null do not create translation span
  // if updateLexical is true, update the active lexical panel
const infoPanel = document.getElementById('info-panel');
const isInfoPanelVisible = infoPanel ? infoPanel.classList.contains('show') : false;
  const activePanel = isInfoPanelVisible
      ? (document.querySelector('#infoPanelTabs .nav-link.active') as HTMLElement).getAttribute('data-bs-target')
      : null;
  const encodedText = encodeURIComponent(selectedText);
  const url = `/translate?text=${encodedText}&book-code=${viewport.bookCode}&lexical-panel=${activePanel || ''}`;

  fetch(url)
    .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
    .then((data: TranslationResponse) => {
        log('Translated:', data);
        if (selectedWordSpans !== null) {
            createAndReplaceTranslationSpan(selectedText, data.translatedText, selectedWordSpans);
        };
        if (updateLexical) {
            updateLexicalPanel(data, activePanel);
        }
    })
    .catch(error => {
      console.error('Error during translation:', error);
    });
}

function updateLexicalPanel(data: TranslationResponse, panelToUpdate: string | null): void {
  const dictionaryPanel = document.getElementById('dictionary-panel-1');
  const explainPanel = document.getElementById('explain-panel');
  const examplesPanel = document.getElementById('examples-panel');

  if (!dictionaryPanel || !explainPanel || !examplesPanel) {
    log('One of the translation panels is missing');
    return;
  }

  if (panelToUpdate === '#dictionary-panel-1' && !currentSelection.updatedPanels.has('#dictionary-panel-1')) {
    dictionaryPanel.innerHTML = data.article;
    currentSelection.updatedPanels.add('#dictionary-panel-1');
  } else if (panelToUpdate === '#explain-panel' && !currentSelection.updatedPanels.has('#explain-panel')) {
    explainPanel.innerHTML = data.article;
    currentSelection.updatedPanels.add('#explain-panel');
  } else if (panelToUpdate === '#examples-panel' && !currentSelection.updatedPanels.has('#examples-panel')) {
    examplesPanel.innerHTML = data.article;
    currentSelection.updatedPanels.add('#examples-panel');
  }
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

function lexicalPanelSwitched(event: Event): void {
    const activePanel = document.querySelector('#infoPanelTabs .nav-link.active')?.getAttribute('data-bs-target') ?? '';
    if (currentSelection.text && !currentSelection.updatedPanels.has(activePanel)) {
      sendTranslationRequest(currentSelection.text, null, true);
    }
}

function clearTranslation(): void {
    currentSelection.text = '';
    currentSelection.updatedPanels.clear();
    const dictionaryPanel = document.getElementById('dictionary-panel-1');
    const explainPanel = document.getElementById('explain-panel');
    const examplesPanel = document.getElementById('examples-panel');

    if (!dictionaryPanel || !explainPanel || !examplesPanel) {
        log('One of the translation panels is missing');
        return;
    }
    dictionaryPanel.innerHTML = 'Loading..';
    explainPanel.innerHTML = 'Loading..';
    examplesPanel.innerHTML = 'Loading..';
}

export { sendTranslationRequest, createAndReplaceTranslationSpan, TranslationResponse, lexicalPanelSwitched, clearTranslation };
