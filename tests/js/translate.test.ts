import { sendTranslationRequest } from '../../lexiflux/viewport/translate';
import * as utilsModule from '../../lexiflux/viewport/utils';
import fetchMock from 'jest-fetch-mock';
import {viewport} from "../../lexiflux/viewport/viewport";

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

