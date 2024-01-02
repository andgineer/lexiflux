import {
  initializeVariables,
  findViewport,
  renderWordsContainer,
  getTotalWords,
  getTopWord,
  findLastVisibleWord, getWordSpans, getWordsContainer,
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

  describe('renderWordsContainer', () => {
    it('should render words in the container', () => {
      renderWordsContainer(0);
      const container = document.getElementById('words-container');
      expect(container).not.toBeNull();
      // Check if the container has the expected content
      // This will depend on how renderWordsContainer works
    });
  });

  describe('findLastVisibleWord', () => {
    it('should find the last visible word in the container', () => {
      // Setup
      const container = getWordsContainer();
      if (!container) {
        throw new Error('Container not found');
      }
      const testWords = ['word1', 'word2', 'word3', 'word4', 'word5'];
      testWords.forEach((word, index) => {
        const span = document.createElement('span');
        span.id = `word-${index}`;
        span.textContent = word;
        container.appendChild(span);
      });

      const wordSpans = getWordSpans();
      wordSpans.length = 0; // Clear the array
      Array.from(container.children).forEach(child => {
        if (child instanceof HTMLElement) {
          wordSpans.push(child);
        }
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
          const index = parseInt(span.id.split('-')[1]);
          let mockRect = {
            top: 0,
            bottom: 0,  // for some reason mocking wordsContainer does not work thus we set 0 to pass as visible
          };
          if (index > 2) {
            // Words after 'word-2' are outside the visible area
            mockRect = {
              top: containerSize + (index - 3) * 20,
              bottom: containerSize + (index - 2) * 20,
            };
          }
          Object.defineProperty(span, 'getBoundingClientRect', {
            value: () => mockRect
          });
        }
      });

      // Test
      const lastWord = findLastVisibleWord();
      expect(lastWord).not.toBeNull();
      expect(lastWord!.id).toBe('word-2')

    });  // it
  }); // findLastVisibleWord

});
