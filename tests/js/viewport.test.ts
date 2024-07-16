import { viewport } from '../../lexiflux/viewport/viewport';

declare const numberOfWords: number;

type MockRectFunction = (id: string) => {
  // Get word ID and return its bounding client rect
  top: number;
  bottom: number;
  left?: number;
  right?: number;
  width?: number;
  height?: number;
};

let mockWordRectFunc: MockRectFunction;
let lastWordId = `word-${numberOfWords - 1}`;

const container = viewport.getWordsContainer();
if (!container) {
  throw new Error('Container not found');
}

const defaultWordRect: DOMRect = {top: 0, bottom: 0, left: 0, right: 0, width: 0, height: 0, x: 0, y: 0, toJSON: () =>{}};
mockWordRectFunc = () => defaultWordRect;

const applyMockRectFunc = () => {
  container.querySelectorAll('.word').forEach(span => {
    if (span.id.match(/^word-\d+$/)) {
      Object.defineProperty(span, 'getBoundingClientRect', {
        value: jest.fn(() => mockWordRectFunc(span.id)),
        configurable: true // Ensure the property can be redefined
      });
    }
  });
};

applyMockRectFunc();
viewport.domChanged();

describe('viewport.js tests', () => {
  describe('initializeVariables', () => {
    it('should initialize variables based on DOM elements', () => {
      expect(viewport.totalWords).toBe(numberOfWords);
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
      mockWordRectFunc = (id: string) => {
        const index = parseInt(id.split('-')[1]);
        const top = viewport.getTopNavbar().getBoundingClientRect().height;
        let mockRect = { top: top, bottom: top }; // Default mock rect
        if (index > 2) {
          mockRect = { top: 1000, bottom: 1020 }; // Words after 'word-2' are lower visible area
        }
        return mockRect;
      };
      applyMockRectFunc();

      const firstWord = viewport.getFirstVisibleWord();
      expect(firstWord).not.toBeNull();
      expect(firstWord).toBe(0);
    });

    it('words from word-2 to word-4 are visible', () => {
      mockWordRectFunc = (id: string) => {
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
      applyMockRectFunc();

      const firstWord = viewport.getFirstVisibleWord();
      expect(firstWord).not.toBeNull();
      expect(firstWord).toBe(2);
    });

    it('should return 0 if all words are outside the visible area', () => {
      mockWordRectFunc = (id: string) => ({top: 1000, bottom: 1020, left: 0, right: 0, width: 0, height: 20});

      const lastWord = viewport.getFirstVisibleWord();
      expect(lastWord).toBe(0);
      expect(viewport.lineHeight).toBe(20);
    });
  });  // findFirstVisibleWord

  describe('scroll', () => {
    beforeEach(() => {
      viewport.getBookPageScroller().scrollTop = 100;
      // mock readonly clientHeight
      Object.defineProperty(viewport.getBookPageScroller(), 'clientHeight', {
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
      viewport.pageNumber = 2; // Not the first page

      const loadPageSpy = jest.spyOn(viewport, 'loadPage');
      await viewport.scrollUp();
      expect(loadPageSpy).toHaveBeenCalledWith(1, undefined); // Expect to load the previous page
      loadPageSpy.mockRestore();
    });

    it('scrollUp: should do nothing if at the top and on the first page', async () => {
      viewport.getBookPageScroller().scrollTop = 0; // Simulate being at the top
      viewport.pageNumber = 1; // The first page

      const scrollTopBefore = viewport.getBookPageScroller().scrollTop;
      await viewport.scrollUp();
      expect(viewport.getBookPageScroller().scrollTop).toBe(scrollTopBefore); // ScrollTop should not change
    });

    it('scrollDown: should scroll down within the same page if not at the bottom', async () => {
      // Mock the bottom of the last wordSpan to simulate not being at the bottom
      mockWordRectFunc = (id: string) => {
        let wordRect: DOMRect = defaultWordRect;
        if (id === lastWordId) { // Words after 'word-2' are lower visible area
          wordRect = {
            top: 0,
            bottom: viewport.getBookPageScroller().getBoundingClientRect().bottom + 100,
            left: 0,
            right: 0,
            width: 0,
            height: 0,
            x: 0,
            y: 0,
            toJSON: () =>{}
          }
        }
        return wordRect;
      };
      applyMockRectFunc();

      const initialScrollTop = viewport.getBookPageScroller().scrollTop;
      await viewport.scrollDown();
      expect(viewport.getBookPageScroller().scrollTop).toBeGreaterThan(initialScrollTop);
    });

  }); // scroll

}); // viewport.js tests
