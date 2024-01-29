import {
  initializeVariables,
  findViewport,
  getTotalWords,
  getFistVisibleWord,
  getWordSpans, getWordsContainer, getTopNavbar,
} from '../../lexiflux/viewport/viewport';


type MockRectFunction = (id: string) => {
  // Get word ID and return its bounding client rect
  top: number;
  bottom: number;
  left?: number;
  right?: number;
  width?: number;
  height?: number
};

let mockWordsRect: MockRectFunction;

describe('viewport.js tests', () => {
  beforeAll(() => {
      const container = getWordsContainer();
      if (!container) {
        throw new Error('Container not found');
      }

      mockWordsRect = () => ({ top: 0, bottom: 0, left: 0, right: 0, width: 0, height: 0 });


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
            value: () => mockWordsRect(span.id)
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
  });

  describe('initializeVariables', () => {
    it('should initialize variables based on DOM elements', () => {
      expect(getTotalWords()).toBe(0);
    });
  });

  describe('findViewport', () => {
    it('should find the correct viewport', () => {
      // This test will depend on how findViewport is implemented
      // and what it's supposed to do
      const result = findViewport(10);
      expect(result).toBeDefined();
    });
  });

  describe('findFirstVisibleWord', () => {

    it('words up to word-2 are visible, so the first visible word is the very first one', () => {
      mockWordsRect = (id: string) => {
        const index = parseInt(id.split('-')[1]);
        const top = getTopNavbar().getBoundingClientRect().height;
        let mockRect = { top: top, bottom: top }; // Default mock rect
        if (index > 2) {
          mockRect = { top: 1000, bottom: 1020 }; // Words after 'word-2' are lower visible area
        }
        return mockRect;
      };

      const firstWord = getFistVisibleWord();
      expect(firstWord).not.toBeNull();
      expect(firstWord).toBe(0);
    });

    it('words from word-2 to word-4 are visible', () => {
      mockWordsRect = (id: string) => {
        const index = parseInt(id.split('-')[1]);
        const top = getTopNavbar().getBoundingClientRect().height;
        let mockRect = { top: top, bottom: top }; // Default mock rect
        if (index < 2) {
          mockRect = { top: -1000, bottom: -1020 }; // Words before 'word-2' are upper visible area
        } else if (index > 4) {
          mockRect = { top: 1000, bottom: 1020 }; // Words after 'word-4' are lower visible area
        }
        return mockRect;
      };

      const firstWord = getFistVisibleWord();
      expect(firstWord).not.toBeNull();
      expect(firstWord).toBe(2);
    });

    it('should return 0 if all words are outside the visible area', () => {
      mockWordsRect = (id: string) => ({ top: 1000, bottom: 1020, left: 0, right: 0, width: 0, height: 0 });

      const lastWord = getFistVisibleWord();
      expect(lastWord).toBe(0);
    });
  });

});
