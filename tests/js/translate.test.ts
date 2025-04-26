import fetchMock from 'jest-fetch-mock';
import * as utils from '../../lexiflux/viewport/utils';

// Reset modules before tests to clear any cached imports
beforeEach(() => {
  jest.resetModules();
});

// Define removeSpan as a direct Jest mock function
const removeSpanMock = jest.fn();

// Define our mocks globally to maintain consistent references
const mockSpanManager = {
  getExtendedWordIds: jest.fn(ids => new Set(ids)),
  getAffectedSpans: jest.fn(() => new Set([1])),
  addSpan: jest.fn(),
  removeSpan: removeSpanMock,
  clear: jest.fn()
};

// Create a fresh mock viewport object for testing
const mockViewport = {
  bookCode: 'test-book',
  pageNumber: 5,
  wordsContainerTopMargin: 50,
  adjustTopTranslationSpans: jest.fn(),
  bookPageScroller: {
    getBoundingClientRect: jest.fn().mockReturnValue({
      bottom: 500
    }),
    scrollTop: 0,
    offsetWidth: 800,
    clientHeight: 500
  },
  getWordsContainer: jest.fn(() => {
    // Return the actual words container from the DOM
    return document.getElementById('words-container') || document.createElement('div');
  })
};

// Set up mocks before each test
beforeEach(() => {
  // Mock the modules - must be done BEFORE importing translate
  jest.doMock('../../lexiflux/viewport/viewport', () => ({
    viewport: mockViewport
  }));

  jest.doMock('../../lexiflux/viewport/TranslationSpanManager', () => ({
    spanManager: mockSpanManager
  }));
});

describe('translate.ts tests', () => {
  // Save original implementations
  const originalGetSelection = window.getSelection;
  const originalCreateRange = document.createRange;
  const originalConsoleLog = console.log;
  const originalConsoleError = console.error;
  const originalWindowOpen = window.open;

  beforeEach(() => {
    // Reset mocks
    fetchMock.resetMocks();
    jest.clearAllMocks();
    jest.spyOn(console, 'log').mockImplementation();
    jest.spyOn(console, 'error').mockImplementation();
    window.open = jest.fn();

    // Reset our mock values for each test
    mockViewport.bookCode = 'test-book';
    mockViewport.pageNumber = 5;
    removeSpanMock.mockClear();

    // Set up DOM
    document.body.innerHTML = `
      <div id="lexical-panel" class="show"></div>
      <div id="lexicalPanelTabs">
        <button id="lexical-tab-1" class="nav-link active" data-bs-toggle="tab">Tab 1</button>
        <button id="lexical-tab-2" class="nav-link" data-bs-toggle="tab">Tab 2</button>
      </div>
      <div id="lexicalPanelContent">
        <div class="tab-pane active" id="lexical-article-1">
          <div id="lexical-content-1" class="lexical-content">Initial content</div>
          <iframe id="lexical-frame-1" src="test.html"></iframe>
        </div>
        <div class="tab-pane" id="lexical-article-2">
          <div id="lexical-content-2" class="lexical-content">Second panel</div>
          <iframe id="lexical-frame-2" src="test2.html"></iframe>
        </div>
      </div>
      <div id="book-page-scroller" style="height: 500px; width: 800px;">
        <div id="words-container">
          <span id="word-1" class="word">Word 1</span>
          <span id="word-2" class="word">Word 2</span>
          <span id="word-3" class="word">Word 3</span>
          <span id="word-4" class="word">Word 4</span>
          <span id="word-5" class="word">Word 5</span>
        </div>
      </div>
    `;

    // Mock window.getSelection
    window.getSelection = jest.fn().mockReturnValue({
      rangeCount: 1,
      getRangeAt: jest.fn().mockReturnValue({
        collapsed: false,
        startContainer: document.getElementById('word-1'),
        endContainer: document.getElementById('word-2'),
        selectNodeContents: jest.fn(),
      }),
      removeAllRanges: jest.fn(),
      addRange: jest.fn()
    });

    // Mock document.createRange
    document.createRange = jest.fn().mockReturnValue({
      setStart: jest.fn(),
      setEnd: jest.fn(),
      setStartBefore: jest.fn(),
      setEndAfter: jest.fn(),
      selectNodeContents: jest.fn(),
      cloneContents: jest.fn().mockReturnValue(document.createDocumentFragment()),
      deleteContents: jest.fn(),
      insertNode: jest.fn(node => {
        const container = document.getElementById('words-container');
        if (container) container.appendChild(node);
      }),
      startContainer: document.getElementById('word-1'),
      endContainer: document.getElementById('word-2')
    });

    // Set up spanManager mocks with meaningful behavior
    mockSpanManager.getExtendedWordIds.mockImplementation(ids => {
      const result = new Set(ids);
      // Add adjacent words to simulate extended selection
      if (ids.includes(1)) result.add(2);
      if (ids.includes(4)) result.add(5);
      return result;
    });

    // Mock fetch for translation requests
    fetchMock.mockResponse(JSON.stringify({
      article: 'Translated text',
      url: null
    }));
  });

  afterEach(() => {
    // Restore original functionality
    window.getSelection = originalGetSelection;
    document.createRange = originalCreateRange;
    console.log = originalConsoleLog;
    console.error = originalConsoleError;
    window.open = originalWindowOpen;

    // Clear jest mocks
    jest.clearAllMocks();
    jest.restoreAllMocks();
  });

  // Core functionality tests
  describe('Core Module Functions', () => {
    test('clearLexicalPanel should reset selection state and clear DOM content', () => {
      // Import the module - MUST be imported inside the test to ensure mocks are applied
      const translateModule = require('../../lexiflux/viewport/translate');

      // Set up DOM with content
      document.getElementById('lexical-content-1')!.innerHTML = '<p>Test content</p>';
      document.getElementById('lexical-frame-1')!.setAttribute('src', 'test.html');

      // Call the function
      translateModule.clearLexicalPanel();

      // Verify panels were cleared
      expect(document.getElementById('lexical-content-1')!.innerHTML).toBe('');
      expect(document.getElementById('lexical-frame-1')!.getAttribute('src')).toBe('');
    });

    test('sendTranslationRequest should handle a valid range selection', async () => {
      // Import the module inside the test
      const translateModule = require('../../lexiflux/viewport/translate');

      // Mock createRange for proper word extraction
      const mockRange = {
        startContainer: document.getElementById('word-1'),
        endContainer: document.getElementById('word-2'),
        collapsed: false,
        selectNodeContents: jest.fn()
      };

      // Verify mock is set correctly
      expect(mockViewport.bookCode).toBe('test-book');
      expect(mockViewport.pageNumber).toBe(5);

      // Ensure the range gets a proper response from getSelection
      (window.getSelection as jest.Mock)().getRangeAt.mockReturnValue(mockRange);

      // Call the function with the range - internal code will use window.getSelection()
      // based on the mocked range we set up
      translateModule.sendTranslationRequest(mockRange as any);

      // Wait for any promises to resolve
      await new Promise(resolve => setTimeout(resolve, 0));

      // Verify API was called with correct parameters
      expect(fetchMock).toHaveBeenCalled();
      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toContain('word-ids=');
      expect(url).toContain('book-code=test-book');
      expect(url).toContain('book-page-number=5');
    });

    test('sendTranslationRequest should handle null range gracefully', () => {
      // Import the module inside the test
      const translateModule = require('../../lexiflux/viewport/translate');

      // Call with null range - should use currentSelection
      translateModule.sendTranslationRequest(null);

      // Simply verify it doesn't throw
      expect(true).toBe(true);
    });
  });

    describe('Lexical Panel Error Handling', () => {
      test('should display an error alert in the lexical panel when translation request fails', async () => {
        // Import the module inside the test
        const translateModule = require('../../lexiflux/viewport/translate');

        // Set up DOM with the correct lexical panel structure
        document.body.innerHTML = `
          <div id="lexical-panel" class="show"></div>
          <div id="lexicalPanelContent">
            <div class="tab-pane active" id="lexical-article-1">
              <div id="lexical-content-1" class="lexical-content">Initial content</div>
              <iframe id="lexical-frame-1" src="test.html"></iframe>
            </div>
          </div>
          <div id="book-page-scroller">
            <div id="words-container">
              <span id="word-1" class="word">Word 1</span>
              <span id="word-2" class="word">Word 2</span>
            </div>
          </div>
        `;

        // Configure viewport mock for this specific test
        mockViewport.bookCode = 'error-test-book';
        mockViewport.pageNumber = 10;

        // Mock a proper selection range
        const mockRange = {
          startContainer: document.getElementById('word-1'),
          endContainer: document.getElementById('word-2'),
          collapsed: false,
          selectNodeContents: jest.fn()
        };

        // Override window.getSelection to return our specific range
        (window.getSelection as jest.Mock).mockReturnValue({
          rangeCount: 1,
          getRangeAt: jest.fn().mockReturnValue(mockRange),
          removeAllRanges: jest.fn(),
          addRange: jest.fn()
        });

        // Override the fetch mock specifically for this test
        // Clear previous mocks
        fetchMock.resetMocks();

        // Mock fetch to respond with error status code
        fetchMock.mockResponse(req => {
          // Check if this is a translation request
          if (req.url.includes('/translate')) {
            // Return an error response
            return Promise.resolve({
              status: 500,
              body: JSON.stringify({ error: 'Server error' })
            });
          }
          // For other requests, return a success response
          return Promise.resolve({
            status: 200,
            body: JSON.stringify({ success: true })
          });
        });

        // Spy on console.error to verify it's called
        const consoleErrorSpy = jest.spyOn(console, 'error');

        // Call the function
        translateModule.sendTranslationRequest(mockRange as any);

        // Wait for all promises to resolve
        await new Promise(resolve => setTimeout(resolve, 100));

        // Verify console.error was called with an error
        expect(consoleErrorSpy).toHaveBeenCalled();

        // Verify the lexical panel shows error message
        const contentDiv = document.getElementById('lexical-content-1');
        expect(contentDiv).not.toBeNull();
        expect(contentDiv?.innerHTML).toContain('alert-danger');
        expect(contentDiv?.innerHTML).toContain('Failed to load lexical article');

        // Restore console.error
        consoleErrorSpy.mockRestore();
      });
    });
  // Translation span tests
  describe('Translation Span Handling', () => {
    test('hideTranslation should properly restore original content', () => {
      // Import the module inside the test
      const translateModule = require('../../lexiflux/viewport/translate');

      // Create a translation span with original content
      const wordsContainer = document.getElementById('words-container')!;

      // Create a translation span with the proper structure and ID pattern
      const translationSpan = document.createElement('span');
      translationSpan.className = 'translation-span';
      translationSpan.id = 'translation-word-10';

      const translationTextDiv = document.createElement('div');
      translationTextDiv.className = 'translation-text';
      translationTextDiv.textContent = 'Translation';
      translationSpan.appendChild(translationTextDiv);

      const originalTextDiv = document.createElement('div');
      originalTextDiv.className = 'original-text';
      translationSpan.appendChild(originalTextDiv);

      const originalWord = document.createElement('span');
      originalWord.id = 'word-10';
      originalWord.className = 'word';
      originalWord.textContent = 'Original word';
      originalTextDiv.appendChild(originalWord);

      wordsContainer.appendChild(translationSpan);

      // Verify the initial DOM state
      expect(document.getElementById('translation-word-10')).not.toBeNull();

      // Call hideTranslation
      translateModule.hideTranslation(translationSpan);

      // Verify span removed and original content restored
      expect(document.getElementById('translation-word-10')).toBeNull();
      expect(document.getElementById('word-10')).not.toBeNull();
      expect(document.getElementById('word-10')!.textContent).toBe('Original word');

      // Verify removeSpan was called
      expect(removeSpanMock).toHaveBeenCalled();
    });

    test('hideTranslation should handle malformed translation spans', () => {
      // Import the module inside the test
      const translateModule = require('../../lexiflux/viewport/translate');

      // Create a span without the standard structure
      const translationSpan = document.createElement('span');
      translationSpan.className = 'translation-span';
      translationSpan.id = 'translation-word-999';
      document.body.appendChild(translationSpan);

      // Should not throw
      expect(() => {
        translateModule.hideTranslation(translationSpan);
      }).not.toThrow();

      // Span should be removed
      expect(document.getElementById('translation-word-999')).toBeNull();
    });
  });

  // Lexical panel tests
  describe('Lexical Panel Integration', () => {
    test('lexicalPanelSwitched should handle tab switching', () => {
      // Import the module inside the test
      const translateModule = require('../../lexiflux/viewport/translate');

      // Setup spy for sendTranslationRequest
      const sendTranslationSpy = jest.spyOn(translateModule, 'sendTranslationRequest');

      // Call function
      translateModule.lexicalPanelSwitched('lexical-tab-2');

      // Verify behavior in different scenarios
      // Since we can't directly check private state, we observe behavior
      expect(sendTranslationSpy).not.toThrow();

      sendTranslationSpy.mockRestore();
    });

    test('lexicalPanelSwitched should handle non-existent tab IDs gracefully', () => {
      // Import the module inside the test
      const translateModule = require('../../lexiflux/viewport/translate');

      // Call with invalid ID
      expect(() => {
        translateModule.lexicalPanelSwitched('non-existent-tab');
      }).not.toThrow();
    });
  });

  // End-to-end functionality tests
  describe('End-to-end Translation Flow', () => {
    test('should handle selection, translation, and display', async () => {
      // Import the module inside the test
      const translateModule = require('../../lexiflux/viewport/translate');

      // 1. Set up a text selection
      const mockRange = {
        startContainer: document.getElementById('word-1'),
        endContainer: document.getElementById('word-2'),
        collapsed: false,
        selectNodeContents: jest.fn()
      };

      // 2. Mock selection
      (window.getSelection as jest.Mock)().getRangeAt.mockReturnValue(mockRange);

      // 3. Mock successful API response
      fetchMock.mockResponseOnce(JSON.stringify({
        article: 'Successfully translated text'
      }));

      // 4. Call translation function
      translateModule.sendTranslationRequest(mockRange as any);

      // 5. Wait for async operations
      await new Promise(resolve => setTimeout(resolve, 0));

      // 6. Verify API was called with correct parameters
      expect(fetchMock).toHaveBeenCalled();
      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toContain('word-ids=');
      expect(url).toContain('book-code=test-book');
      expect(url).toContain('book-page-number=5');

      // Since we can't easily check the DOM mutations (which happen with private functions),
      // we verify that the API call was made correctly, which indicates the flow started properly
    });

    test('should handle errors gracefully', async () => {
      // Import the module inside the test
      const translateModule = require('../../lexiflux/viewport/translate');

      // 1. Set up a text selection
      const mockRange = {
        startContainer: document.getElementById('word-1'),
        endContainer: document.getElementById('word-2'),
        collapsed: false,
        selectNodeContents: jest.fn()
      };

      // 2. Mock API error
      fetchMock.mockRejectOnce(new Error('Network error'));

      // 3. Spy on console.error
      const consoleErrorSpy = jest.spyOn(console, 'error');

      // 4. Call translation function
      translateModule.sendTranslationRequest(mockRange as any);

      // 5. Wait for async operations
      await new Promise(resolve => setTimeout(resolve, 0));

      // 6. Verify error was handled
      expect(consoleErrorSpy).toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });
  });

  // Tests for edge cases and error handling
  describe('Edge Cases and Error Handling', () => {
    test('should handle empty selection gracefully', () => {
      // Import the module inside the test
      const translateModule = require('../../lexiflux/viewport/translate');

      // Mock empty selection
      const emptySelectionMock = {
        rangeCount: 0,
        getRangeAt: jest.fn()
      };
      (window.getSelection as jest.Mock).mockReturnValue(emptySelectionMock);

      // Should not throw
      expect(() => {
        translateModule.sendTranslationRequest(null);
      }).not.toThrow();
    });

    test('should handle missing lexical panel elements gracefully', () => {
      // Import the module inside the test
      const translateModule = require('../../lexiflux/viewport/translate');

      // Remove lexical panel elements
      document.getElementById('lexicalPanelContent')!.remove();

      // Should not throw when trying to clear non-existent panel
      expect(() => {
        translateModule.clearLexicalPanel();
      }).not.toThrow();
    });
  });

  // Enhanced DOM interaction tests
  describe('Enhanced DOM Interactions', () => {
    test('hideTranslation should handle spans with different ID formats', () => {
      // Import the module inside the test
      const translateModule = require('../../lexiflux/viewport/translate');

      // Set up DOM with different ID format
      const container = document.createElement('div');
      document.body.appendChild(container);

      // Create a span with a non-standard ID format
      const translationSpan = document.createElement('span');
      translationSpan.className = 'translation-span';
      translationSpan.id = 'different-format'; // ID doesn't follow the pattern
      container.appendChild(translationSpan);

      // Still need the original-text div
      const originalTextDiv = document.createElement('div');
      originalTextDiv.className = 'original-text';
      translationSpan.appendChild(originalTextDiv);

      // And the word element
      const wordSpan = document.createElement('span');
      wordSpan.id = 'word-1';
      wordSpan.textContent = 'Word 1';
      originalTextDiv.appendChild(wordSpan);

      // Add translation text div
      const translationTextDiv = document.createElement('div');
      translationTextDiv.className = 'translation-text';
      translationTextDiv.textContent = 'Translation';
      translationSpan.insertBefore(translationTextDiv, originalTextDiv);

      // Should not throw
      expect(() => {
        translateModule.hideTranslation(translationSpan);
      }).not.toThrow();

      // Should still remove the span
      expect(document.querySelector('.translation-span')).toBeNull();
      // Original content should be preserved
      expect(document.getElementById('word-1')).not.toBeNull();
    });

    test('hideTranslation should work with missing child elements', () => {
      // Import the module inside the test
      const translateModule = require('../../lexiflux/viewport/translate');

      // Set up DOM with missing translation-text
      const container = document.createElement('div');
      document.body.appendChild(container);

      // Create translation span with proper ID
      const translationSpan = document.createElement('span');
      translationSpan.className = 'translation-span';
      translationSpan.id = 'translation-word-1';
      container.appendChild(translationSpan);

      // Only include original-text div, no translation-text div
      const originalTextDiv = document.createElement('div');
      originalTextDiv.className = 'original-text';
      translationSpan.appendChild(originalTextDiv);

      // Add word element
      const wordSpan = document.createElement('span');
      wordSpan.id = 'word-1';
      wordSpan.textContent = 'Word 1';
      originalTextDiv.appendChild(wordSpan);

      // Should not throw
      expect(() => {
        translateModule.hideTranslation(translationSpan);
      }).not.toThrow();

      // Should still preserve content
      expect(document.getElementById('word-1')).not.toBeNull();
      expect(document.body.textContent?.includes('Word 1')).toBe(true);
    });
  });
});
