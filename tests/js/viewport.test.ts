import {
  initializeVariables,
  findViewport,
  getTotalWords,
  getTopWord,
  getWordSpans, getWordsContainer,
} from '../../lexiflux/viewport/viewport';

describe('viewport.js tests', () => {

  beforeEach(() => {
    // Mocking document body for testing DOM manipulation
    document.body.innerHTML = `
      <div id="words-container"></div>
      <div id="book" data-book-id="123" data-page-number="1" data-click-word-url="/click-word"></div>
    `;
    initializeVariables();
  });

  describe('initializeVariables', () => {
    it('should initialize variables based on DOM elements', () => {
      expect(getTotalWords()).toBe(0);
      expect(getTopWord()).toBe(0);
      // Add more assertions based on what initializeVariables does
    });
  });

  describe('findViewport', () => {
    it('should find the correct viewport', () => {
      // This test will depend on how findViewport is implemented
      // and what it's supposed to do
      const result = findViewport(10);
      expect(result).toBeDefined();
      // Add more assertions based on expected behavior
    });
  });

  describe('findLastVisibleWord', () => {
    type MockRectFunction = (id: string) => {
      top: number;
      bottom: number;
      left?: number;
      right?: number;
      width?: number;
      height?: number
    };

    function setupTestEnvironment(mockRectFn: MockRectFunction) {
      // Common setup function
      const container = getWordsContainer();
      if (!container) {
        throw new Error('Container not found');
      }

      // Create and append test words to the container
      const testWords = ['word1', 'word2', 'word3', 'word4', 'word5'];
      testWords.forEach((word, index) => {
        const span = document.createElement('span');
        span.id = `word-${index}`;
        span.textContent = word;
        container.appendChild(span);
      });

      const containerSize = 60;
      Object.defineProperty(container, 'getBoundingClientRect', {
        value: () => ({
          top: 0,
          bottom: containerSize,
          left: 0,
          right: 100,
          width: 100,
          height: containerSize,
          x: 0,
          y: 0
        })
      });

      const spans = Array.from(container.children);
      spans.forEach(span => {
        if (span.id.match(/^word-\d+$/)) {
          Object.defineProperty(span, 'getBoundingClientRect', {
            value: () => mockRectFn(span.id)
          });
        }
      });

      const wordSpans = getWordSpans();
      wordSpans.length = 0; // Clear the array
      spans.forEach(child => {
        if (child instanceof HTMLElement) {
          wordSpans.push(child);
        }
      });
    }

    it('should find the last visible word in the container', () => {
      setupTestEnvironment((id: string) => {
        const index = parseInt(id.split('-')[1]);
        let mockRect = { top: 0, bottom: 0 }; // Default mock rect
        if (index > 2) {
          mockRect = { top: 1000, bottom: 1020 }; // Outside the visible area for words after 'word-2'
        }
        return mockRect;
      });

      // Test
      const lastWord = findLastVisibleWord();
      expect(lastWord).not.toBeNull();
      if (!lastWord) {
        throw new Error('lastWord is null');
      }
      expect(lastWord.id).toBe('word-2');
    });

    it('should return the last word if all words are visible', () => {
      setupTestEnvironment(() => ({ top: 0, bottom: 0, left: 0, right: 0, width: 0, height: 0 }));

      // Test
      const lastWord = findLastVisibleWord();
      expect(lastWord).not.toBeNull();
      if (!lastWord) {
        throw new Error('lastWord is null');
      }
      expect(lastWord.id).toBe('word-4');
    });

    it('should return null if all words are outside the visible area', () => {
      setupTestEnvironment(() => ({ top: 1000, bottom: 1020, left: 0, right: 0, width: 0, height: 0 }));

      // Test
      const lastWord = findLastVisibleWord();
      expect(lastWord).toBeNull();
    });
  }); // findLastVisibleWord

});
