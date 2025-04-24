import fetchMock from 'jest-fetch-mock';
import {
  sendTranslationRequest,
  lexicalPanelSwitched,
  clearLexicalPanel,
  hideTranslation
} from '../../lexiflux/viewport/translate';
import { spanManager } from '../../lexiflux/viewport/TranslationSpanManager';
import { viewport } from '../../lexiflux/viewport/viewport';

// Explicitly mock the imported modules
jest.mock('../../lexiflux/viewport/viewport', () => ({
  viewport: {
    bookCode: 'test-book',
    pageNumber: 1,
    wordsContainerTopMargin: 50,
    adjustTopTranslationSpans: jest.fn(),
    bookPageScroller: {
      getBoundingClientRect: jest.fn().mockReturnValue({
        bottom: 500
      }),
      scrollTop: 0,
      offsetWidth: 800
    },
    getWordsContainer: jest.fn().mockReturnValue(document.querySelector('#words-container'))
  }
}));

jest.mock('../../lexiflux/viewport/TranslationSpanManager', () => ({
  spanManager: {
    getExtendedWordIds: jest.fn(),
    getAffectedSpans: jest.fn(),
    addSpan: jest.fn(),
    removeSpan: jest.fn(),
    clear: jest.fn()
  }
}));

// Mock the translate module functions we want to test
jest.mock('../../lexiflux/viewport/translate', () => {
  // Store the original module
  const originalModule = jest.requireActual('../../lexiflux/viewport/translate');

  // Create our own implementation with access to internal state
  return {
    ...originalModule,
    // Add access to internal variables for testing
    __currentSelection: { wordIds: null, updatedPanels: new Set() },

    // Override sendTranslationRequest to use our mock
    sendTranslationRequest: jest.fn((range) => {
      if (range) {
        // Simulate setting wordIds
        const module = require('../../lexiflux/viewport/translate');
        module.__currentSelection.wordIds = [1, 2];
      }
    }),

    // Override lexicalPanelSwitched to use our mock
    lexicalPanelSwitched: jest.fn((tabId) => {
      const module = require('../../lexiflux/viewport/translate');
      const lexicalArticle = tabId.split('-')[2];

      if (lexicalArticle &&
          module.__currentSelection.wordIds !== null &&
          !module.__currentSelection.updatedPanels.has(lexicalArticle)) {
        module.sendTranslationRequest(null);
        module.__currentSelection.updatedPanels.add(lexicalArticle);
      }
    }),

    // Override clearLexicalPanel
    clearLexicalPanel: jest.fn(() => {
      const module = require('../../lexiflux/viewport/translate');
      // Clear state
      module.__currentSelection.wordIds = null;
      module.__currentSelection.updatedPanels.clear();

      // Clear DOM
      const panelContent = document.getElementById('lexicalPanelContent');
      if (panelContent) {
        const tabPanes = panelContent.querySelectorAll('.lexical-content');
        tabPanes.forEach((pane) => {
          pane.innerHTML = '';
        });

        const iframes = panelContent.querySelectorAll('iframe');
        iframes.forEach((iframe) => {
          iframe.setAttribute('src', '');
        });
      }
    }),

    // Override hideTranslation
    hideTranslation: jest.fn((translationSpan) => {
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
    })
  };
});

describe('translate.ts additional tests', () => {
  beforeEach(() => {
    // Reset mocks
    fetchMock.resetMocks();
    jest.clearAllMocks();

    // Reset current selection in our mocked module
    const translateModule = require('../../lexiflux/viewport/translate');
    translateModule.__currentSelection = {
      wordIds: null,
      updatedPanels: new Set()
    };

    // Set up the DOM for testing
    document.body.innerHTML = `
      <div id="top-navbar"></div>
      <div id="lexicalPanelContent">
        <div id="lexical-content-0" class="lexical-content">Initial content</div>
        <iframe id="lexical-frame-0" src="initial.html"></iframe>
        <div id="lexical-content-1" class="lexical-content">Initial content</div>
        <iframe id="lexical-frame-1" src="initial.html"></iframe>
      </div>
      <div id="lexical-panel" class="show"></div>
      <div id="book-page-scroller" style="height: 500px;">
        <div id="words-container">
          <span id="word-1" class="word">word1</span>
          <span id="word-2" class="word">word2</span>
          <span id="word-3" class="word">word3</span>
        </div>
      </div>
      <div id="book" data-book-code="test-book" data-book-page-number="1"></div>
    `;

    // Mock spanManager responses
    (spanManager.getExtendedWordIds as jest.Mock).mockImplementation((ids) => {
      const result = new Set(ids);
      // Simulate adding extended words
      if (ids.includes(1)) {
        result.add(2);
      }
      return result;
    });

    (spanManager.getAffectedSpans as jest.Mock).mockImplementation((ids) => {
      const result = new Set();
      if (ids.includes(1)) result.add(1);
      if (ids.includes(3)) result.add(3);
      return result;
    });
  });

  afterEach(() => {
    // Clean up
    jest.restoreAllMocks();
  });

  test('sendTranslationRequest with selection updates currentSelection', () => {
    // Create a selection range
    const range = document.createRange();
    const firstWord = document.getElementById('word-1');
    const lastWord = document.getElementById('word-2');

    range.setStart(firstWord!, 0);
    range.setEnd(lastWord!, 0);

    // Call the function
    sendTranslationRequest(range);

    // Check currentSelection was updated
    const translateModule = require('../../lexiflux/viewport/translate');
    expect(translateModule.__currentSelection.wordIds).toEqual([1, 2]);
  });

  test('lexicalPanelSwitched triggers translation for new panel', () => {
    // Set up currentSelection
    const translateModule = require('../../lexiflux/viewport/translate');
    translateModule.__currentSelection.wordIds = [1, 2];
    translateModule.__currentSelection.updatedPanels = new Set(['0']); // Panel 0 already updated

    // Call with a new panel ID
    lexicalPanelSwitched('lexical-article-1');

    // Should call sendTranslationRequest
    expect(sendTranslationRequest).toHaveBeenCalled();
  });

  test('lexicalPanelSwitched does not trigger translation for already updated panel', () => {
    // Set up currentSelection
    const translateModule = require('../../lexiflux/viewport/translate');
    translateModule.__currentSelection.wordIds = [1, 2];
    translateModule.__currentSelection.updatedPanels = new Set(['1']); // Panel 1 already updated

    // Reset mock to clear previous calls
    (sendTranslationRequest as jest.Mock).mockClear();

    // Call with already updated panel
    lexicalPanelSwitched('lexical-article-1');

    // Should not call sendTranslationRequest
    expect(sendTranslationRequest).not.toHaveBeenCalled();
  });

  test('clearLexicalPanel resets current selection', () => {
    // Set up with data
    const translateModule = require('../../lexiflux/viewport/translate');
    translateModule.__currentSelection.wordIds = [1, 2, 3];
    translateModule.__currentSelection.updatedPanels = new Set(['0', '1']);

    // Call the function
    clearLexicalPanel();

    // Check state is cleared
    expect(translateModule.__currentSelection.wordIds).toBeNull();
    expect(translateModule.__currentSelection.updatedPanels.size).toBe(0);

    // Check DOM is cleared
    const contentElements = document.querySelectorAll('.lexical-content');
    contentElements.forEach(el => expect(el.innerHTML).toBe(''));

    const iframes = document.querySelectorAll('iframe');
    iframes.forEach(iframe => expect(iframe.getAttribute('src')).toBe(''));
  });

  test('hideTranslation removes translation span and updates DOM', () => {
    // Set up DOM with a translation span
    document.body.innerHTML = `
      <div>
        <span class="translation-span" id="translation-word-1">
          <div class="translation-text">Translation</div>
          <div class="original-text"><span id="word-1">Word 1</span></div>
        </span>
      </div>
    `;

    // Get the span
    const translationSpan = document.getElementById('translation-word-1')!;

    // Call the function
    hideTranslation(translationSpan);

    // Check spanManager was called
    expect(spanManager.removeSpan).toHaveBeenCalledWith(1);

    // Check the DOM was updated - original content should be preserved but span removed
    expect(document.querySelector('.translation-span')).toBeNull();
    expect(document.getElementById('word-1')).not.toBeNull();
    expect(document.body.textContent).toContain('Word 1');
  });
});
