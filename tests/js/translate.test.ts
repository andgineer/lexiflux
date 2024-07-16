// tests/js/translation.test.ts
import fetchMock from 'jest-fetch-mock';
import {
  sendTranslationRequest,
  lexicalPanelSwitched,
  clearLexicalPanel,
  hideTranslation
} from '../../lexiflux/viewport/translate';

fetchMock.enableMocks();

declare global {
  var htmx: { process: jest.Mock };
  var numberOfWords: number;
  var currentSelection: { wordIds: number[] | null; updatedPanels: Set<any> };
}

describe('translate.ts tests', () => {
  beforeEach(() => {
    // Set up the DOM and mocks before each test
    document.body.innerHTML = `
      <div id="top-navbar"></div>
      <div id="lexicalPanelContent"></div>
      <div id="book-page-scroller" style="height: 500px;">
        <div id="words-container"></div>
      </div>
      <div id="book" data-book-code="alice-adventures-carroll" data-book-page-number="1" data-click-word-url="/click-word"></div>
    `;

    global.htmx = { process: jest.fn() };
    global.numberOfWords = 5;
  });


  test('clearLexicalPanel clears the lexical panel content', () => {
    document.body.innerHTML = `
      <div id="lexicalPanelContent">
        <div class="lexical-content">Old Content</div>
        <iframe src="old"></iframe>
      </div>
    `;

    global.currentSelection = { wordIds: [1, 2, 3], updatedPanels: new Set<unknown>() };

    clearLexicalPanel();

    const panelContent = document.getElementById('lexicalPanelContent')!;
    expect(panelContent.innerHTML).toBe(`
        <div class="lexical-content"></div>
        <iframe src=""></iframe>
      `);
  });

  test('hideTranslation hides the translation for a specific word', () => {
    document.body.innerHTML = `
      <span class="translation-span" id="translation">
        <div class="translation-text">Translation</div>
        <div class="original-text"> <span id="word-1">Word 1</span> </div>
      </span>
    `;

    const translationSpan = document.getElementById('translation')!;
    hideTranslation(translationSpan);

    expect(document.body.innerHTML.trim()).toBe(`<span id="word-1">Word 1</span>`);
  });
});
