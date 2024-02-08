import {createAndReplaceTranslationSpan, sendTranslationRequest} from '../../lexiflux/viewport/translate';
import * as utilsModule from '../../lexiflux/viewport/utils';
import fetchMock from 'jest-fetch-mock';
import {viewport} from "../../lexiflux/viewport/viewport";

Object.defineProperty(viewport.bookPageScroller, 'getBoundingClientRect', {
    value: () => ({
        bottom: -600,  // negative 'cause it's complicated to mock rects for elements created inside code under test
        height: 500,
        top: 100,
        left: 0,
        right: 0,
        width: 800,
        x: 0,
        y: 100,
        toJSON: () => {},
    }),
});

describe('translate.ts', () => {
    beforeEach(() => {
        // Reset fetch mocks and DOM changes before each test
        fetchMock.resetMocks();

        // Explicitly mock insertBefore and removeChild as jest.fn()
        const mockInsertBefore = jest.fn();
        const mockRemoveChild = jest.fn();

        const mockGetWordsContainer = jest.fn().mockImplementation(() => ({
            insertBefore: mockInsertBefore,
            removeChild: mockRemoveChild,
            getBoundingClientRect: jest.fn(() => ({ bottom: 200 })),
        }));

        const mockBookPageScroller = {
            scrollTop: 100,
            clientHeight: 500,
            getBoundingClientRect: jest.fn(() => ({ bottom: 600 })),
        };

        jest.mock('../../lexiflux/viewport/viewport', () => ({
            getWordsContainer: mockGetWordsContainer,
            bookPageScroller: mockBookPageScroller,
        }));
    });

    it('ensures translated text is visible', async () => {
        // Setup the scenario where the translated text would be out of view initially
        const initialScrollTop = viewport.bookPageScroller.scrollTop;
        const translatedText = 'translated text';
        let spanElement = document.createElement('span');
        spanElement.id = 'word-1';
        spanElement.textContent = 'original text';
        const selectedWordSpans = [spanElement];
        viewport.wordsContainer.appendChild(selectedWordSpans[0]);
        createAndReplaceTranslationSpan('original text', translatedText, selectedWordSpans);

        // Assert the page was scrolled to make the translation visible
        expect(viewport.bookPageScroller.scrollTop).toBeGreaterThan(initialScrollTop);
    });

  it('sends a translation request and updates the sidebar on success', async () => {
    // Mock successful fetch response
    fetchMock.mockResponseOnce(JSON.stringify({
      translatedText: 'translated text',
      article: 'translated article',
    }));

    // Mock selected text and elements
    const selectedText = 'test';
    const range = document.createRange(); // Mock range if needed
    const selectedWordSpans = [document.createElement('span')];
    viewport.getWordsContainer().insertBefore(selectedWordSpans[0], null);

    await sendTranslationRequest(selectedText, range, selectedWordSpans);

    // Check if fetch was called correctly
    expect(fetchMock).toHaveBeenCalledWith('/translate?text=test');
    // todo: Check if translation was added
  });

  // todo: more tests here for other functionalities like
  // - Testing ensureVisible logic
  // - Testing createAndReplaceTranslationSpan function directly with mocked inputs
  // - Error cases, e.g., what happens when the sidebar doesn't exist or fetch fails
});

