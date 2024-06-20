// translate.ts
import { log } from './utils'; // Assuming log function is used here
import { viewport } from './viewport'; // If viewport functionalities are required

interface TranslationResponse {
  translatedText: string;
  article: string;
}

function sendTranslationRequest(selectedText: string, range: Range, selectedWordSpans: HTMLElement[]): void {
  const infoPanel = document.getElementById('info-panel');
  const isInfoPanelVisible = infoPanel && infoPanel.classList.contains('show');
  const encodedText = encodeURIComponent(selectedText);
  const url = `/translate?text=${encodedText}&book-code=${viewport.bookCode}&full=${isInfoPanelVisible}`;

  fetch(url)
    .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
    .then((data: TranslationResponse) => {
        log('Translated:', data);
        createAndReplaceTranslationSpan(selectedText, data.translatedText, selectedWordSpans);

        const dictionaryPanel = document.getElementById('dictionary-panel-1');
        const explainPanel = document.getElementById('explain-panel');
        const examplesPanel = document.getElementById('examples-panel');
        if (!dictionaryPanel || !explainPanel || !examplesPanel) {
            log('One of the translation panels is missing');
            return;
        }
        dictionaryPanel.innerHTML = data.article;
        if (isInfoPanelVisible) {
            log('Info panel is visible');
        } else {
            log('Info panel is not visible');
            explainPanel.innerHTML = '';
            examplesPanel.innerHTML = '';
        }
    })
    .catch(error => {
      console.error('Error during translation:', error);
    });
}

function ensureVisible(element: HTMLSpanElement) {
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

export { sendTranslationRequest, createAndReplaceTranslationSpan, TranslationResponse };
