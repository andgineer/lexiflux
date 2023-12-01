const { wordsInViewport } = require('../../lexiflux/static/lexiflux/viewport.js');

describe('wordsInViewport', () => {
    it('should calculate visible words correctly', () => {
        // Mock the getBoundingClientRect function
        const mockGetBoundingClientRect = jest.fn(() => ({
            bottom: 100,
            height: 20
        }));
        global.document.getElementById = jest.fn(() => ({
            getBoundingClientRect: mockGetBoundingClientRect
        }));

        const visibleWords = wordsInViewport();
        expect(visibleWords).toBe(/* expected number */);
    });
});
