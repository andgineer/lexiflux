// translate.ts
import { log } from './utils'; // Assuming log function is used here
import { viewport } from './viewport'; // If viewport functionalities are required

interface TranslationResponse {
  translatedText: string;
  article: string;
}

function sendTranslationRequest(selectedText: string, range: Range, selectedWordSpans: HTMLElement[]): void {
  const encodedText = encodeURIComponent(selectedText);
  const url = `/translate?text=${encodedText}`;

  fetch(url)
    .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
    .then((data: TranslationResponse) => {
      log('Translated:', data);
      const sidebar = document.getElementById('sidebar');
      if (sidebar) {
        sidebar.innerHTML = data.article; // Set innerHTML only if sidebar is not null
      } else {
        console.error('Sidebar element not found');
      }
      createAndReplaceTranslationSpan(selectedText, data.translatedText, selectedWordSpans);
    })
    .catch(error => {
      console.error('Error during translation:', error);
    });
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
}

export { sendTranslationRequest, createAndReplaceTranslationSpan, TranslationResponse };
