import { viewport } from '../../lexiflux/viewport/viewport';

type MockRectFunction = (id: string) => {
  // Get word ID and return its bounding client rect
  top: number;
  bottom: number;
  left?: number;
  right?: number;
  width?: number;
  height?: number;
};

let mockWordRect: MockRectFunction;

describe('viewport.js tests', () => {
  beforeAll(() => {
    viewport.initializeVariables();

    const container = viewport.getWordsContainer();
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
    const mockContainerRect = (): DOMRect => ({
      top: 0,
      bottom: containerSize,
      left: 0,
      right: 100,
      width: 100,
      height: containerSize,
      x: 0,
      y: 0,
      toJSON: () => {}, // Adding the toJSON method to satisfy TypeScript
    });

    Object.defineProperty(viewport.wordsContainer, 'getBoundingClientRect', {
      value: () => mockContainerRect
    });

    mockWordRect = () => ({top: 0, bottom: 0, left: 0, right: 0, width: 0, height: 0});
    const spans = Array.from(container.children);
    spans.forEach(span => {
      if (span.id.match(/^word-\d+$/)) {
        Object.defineProperty(span, 'getBoundingClientRect', {
          value: () => mockWordRect(span.id)
        });
      }
    });

    viewport.wordSpans.length = 0; // Clear the array
    spans.forEach(child => {
      if (child instanceof HTMLElement) {
        viewport.wordSpans.push(child);
      }
    });
  });  // beforeAll

  describe('initializeVariables', () => {
    it('should initialize variables based on DOM elements', () => {
      expect(viewport.totalWords).toBe(0);
    });
  });

  describe('findViewport', () => {
    it('should find the correct viewport', () => {
      const result = viewport.getWordTop(10);
      expect(result).toBeDefined();
    });
  }); // findViewport

  describe('findFirstVisibleWord', () => {
    it('words up to word-2 are visible, so the first visible word is the very first one', () => {
      mockWordRect = (id: string) => {
        const index = parseInt(id.split('-')[1]);
        const top = viewport.getTopNavbar().getBoundingClientRect().height;
        let mockRect = { top: top, bottom: top }; // Default mock rect
        if (index > 2) {
          mockRect = { top: 1000, bottom: 1020 }; // Words after 'word-2' are lower visible area
        }
        return mockRect;
      };

      const firstWord = viewport.getFirstVisibleWord();
      expect(firstWord).not.toBeNull();
      expect(firstWord).toBe(0);
    });

    it('words from word-2 to word-4 are visible', () => {
      mockWordRect = (id: string) => {
        const index = parseInt(id.split('-')[1]);
        const top = viewport.getTopNavbar().getBoundingClientRect().height;
        let mockRect = { top: top, bottom: top }; // Default mock rect
        if (index < 2) {
          mockRect = { top: -1000, bottom: -1020 }; // Words before 'word-2' are upper visible area
        } else if (index > 4) {
          mockRect = { top: 1000, bottom: 1020 }; // Words after 'word-4' are lower visible area
        }
        return mockRect;
      };

      const firstWord = viewport.getFirstVisibleWord();
      expect(firstWord).not.toBeNull();
      expect(firstWord).toBe(2);
    });

    it('should return 0 if all words are outside the visible area', () => {
      mockWordRect = (id: string) => ({top: 1000, bottom: 1020, left: 0, right: 0, width: 0, height: 20});

      const lastWord = viewport.getFirstVisibleWord();
      expect(lastWord).toBe(0);
      expect(viewport.lineHeight).toBe(20);
    });
  });  // findFirstVisibleWord

  describe('scroll', () => {
    beforeEach(() => {
      viewport.pageScroller.scrollTop = 100;
      // mock readonly clientHeight
      Object.defineProperty(viewport.pageScroller, 'clientHeight', {
        value: 100,
        writable: true
      });
    });

    it('scrollUp: should scroll up within the same page if not at the top', async () => {
      const initialScrollTop = viewport.getBookPageScroller().scrollTop;
      await viewport.scrollUp();
      expect(viewport.getBookPageScroller().scrollTop).toBeLessThan(initialScrollTop);
    });

    it('scrollUp: should load the previous page if at the top and not on the first page', async () => {
      viewport.getBookPageScroller().scrollTop = 0; // Simulate being at the top
      viewport.pageNum = 2; // Not the first page

      const loadPageSpy = jest.spyOn(viewport, 'loadPage');
      await viewport.scrollUp();
      expect(loadPageSpy).toHaveBeenCalledWith(1, 0); // Expect to load the previous page
      loadPageSpy.mockRestore();
    });

    it('scrollUp: should do nothing if at the top and on the first page', async () => {
      viewport.getBookPageScroller().scrollTop = 0; // Simulate being at the top
      viewport.pageNum = 1; // The first page

      const scrollTopBefore = viewport.getBookPageScroller().scrollTop;
      await viewport.scrollUp();
      expect(viewport.getBookPageScroller().scrollTop).toBe(scrollTopBefore); // ScrollTop should not change
    });

    it('scrollDown: should scroll down within the same page if not at the bottom', async () => {
      // Mock the bottom of the last wordSpan to simulate not being at the bottom
      const mockBottom = viewport.getBookPageScroller().getBoundingClientRect().bottom + 100;
      Object.defineProperty(viewport.wordSpans[viewport.wordSpans.length - 1], 'getBoundingClientRect', {
        value: () => ({ bottom: mockBottom }),
        configurable: true,
      });

      const initialScrollTop = viewport.getBookPageScroller().scrollTop;
      await viewport.scrollDown();
      expect(viewport.getBookPageScroller().scrollTop).toBeGreaterThan(initialScrollTop);
    });

    it('scrollDown: should load the next page if at the bottom', async () => {
      // Simulate the last word being within the viewport to trigger loading the next page
      const mockBottom = viewport.getBookPageScroller().getBoundingClientRect().bottom - 1;
      Object.defineProperty(viewport.wordSpans[viewport.wordSpans.length - 1], 'getBoundingClientRect', {
        value: () => ({ bottom: mockBottom }),
        configurable: true,
      });

      viewport.pageNum = 1; // Current page
      const loadPageSpy = jest.spyOn(viewport, 'loadPage');
      await viewport.scrollDown();
      expect(loadPageSpy).toHaveBeenCalledWith(2, 0); // Expect to load the next page
      loadPageSpy.mockRestore();
    });
  }); // scroll

}); // viewport.js tests
