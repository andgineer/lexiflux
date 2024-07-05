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

jest.spyOn(viewport.getWordsContainer(), 'insertBefore')
  .mockImplementation((node, child) => node);
jest.spyOn(viewport.getWordsContainer(), 'removeChild')
  .mockImplementation((child) => child);

describe('translate.ts', () => {
    let originalDocument: Document | null;

    beforeEach(() => {
      originalDocument = global.document;
    });

    afterEach(() => {
      global.document = originalDocument || document;
    });

    it('ensures translated text is visible', async () => {
        // Setup the scenario where the translated text would be out of view initially
        const initialScrollTop = viewport.bookPageScroller.scrollTop;
        const translatedText = 'translated text';
        let spanElement = document.createElement('span');
        spanElement.id = 'word-1';
        spanElement.textContent = 'original text';
        const selectedWordSpans = [spanElement];
        createAndReplaceTranslationSpan('original text', translatedText, selectedWordSpans);

        // Assert the page was scrolled to make the translation visible
        expect(viewport.bookPageScroller.scrollTop).toBeGreaterThan(initialScrollTop);
    });

  it('sends a translation request and creates and replaces translation span correctly', async () => {
    // Mock selected text and elements
    const selectedText = 'test';
    const range = document.createRange(); // Mock range if needed
    let spanElement = document.createElement('span');
    spanElement.id = 'word-1';
    spanElement.textContent = 'original text';
    const selectedWordSpans = [spanElement];
    viewport.getWordsContainer().insertBefore(selectedWordSpans[0], null);

    await sendTranslationRequest(["1","2"], selectedWordSpans);

    // Check if fetch was called correctly
    expect(fetchMock).toHaveBeenCalledWith('/translate?word-ids=1.2&book-code=&book-page-number=0');
    // Check if translation was added
    expect(viewport.getWordsContainer().insertBefore).toHaveBeenCalled();
    // Assert the original word spans were removed
    expect(viewport.getWordsContainer().removeChild).toHaveBeenCalledWith(selectedWordSpans[0]);
  });

  it('handles missing sidebar gracefully', async () => {
    document.body.innerHTML = ''; // Simulate missing sidebar
    const selectedText = 'test';
    const range = document.createRange();
    const selectedWordSpans = [document.createElement('span')];

    await sendTranslationRequest(["1","2"], selectedWordSpans);

    // Expect no errors thrown, can also check for specific log output if necessary
    expect(fetchMock).toHaveBeenCalled();
  });

  it('handles fetch failure gracefully', async () => {
    fetchMock.resetMocks();
    fetchMock.mockRejectOnce(new Error('Network failure'));
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});


    const selectedText = 'test';
    const range = document.createRange();
    const selectedWordSpans = [document.createElement('span')];

    sendTranslationRequest(["1","2"], selectedWordSpans);

    // Since sendTranslationRequest does not return a promise, we cannot directly await it.
    // However, we can wait for the next tick to allow any promises within sendTranslationRequest to resolve/reject.
    return new Promise<void>((resolve) => {
        setTimeout(() => {
            expect(consoleSpy).toHaveBeenCalledWith(
                expect.stringContaining('Error during translation:'),
                expect.objectContaining({ message: expect.stringContaining('Network failure') })
            );
            consoleSpy.mockRestore(); // Clean up the spy
            resolve(); // Correct usage when the promise is typed as Promise<void>
        }, 0); // Use 0 ms delay to schedule for the next tick
    });


  });

});

