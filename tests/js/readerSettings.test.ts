import fetchMock from 'jest-fetch-mock';
import {
  initializeReaderSettings,
  initializeReaderEventListeners,
  ReaderSettings
} from '../../lexiflux/viewport/readerSettings';
import { viewport } from '../../lexiflux/viewport/viewport';
import * as utils from '../../lexiflux/viewport/utils';

// Mock dependencies
jest.mock('../../lexiflux/viewport/viewport', () => ({
  viewport: {
    bookCode: 'test-book',
    getWordsContainer: jest.fn()
  }
}));

jest.mock('../../lexiflux/viewport/utils', () => ({
  showModal: jest.fn(),
  closeModal: jest.fn()
}));

describe('readerSettings.ts tests', () => {
  let mockWordsContainer: HTMLElement;

  beforeEach(() => {
    // Clear mocks and reset DOM
    fetchMock.resetMocks();
    jest.clearAllMocks();

    // Set up DOM elements needed by the functions
    document.body.innerHTML = `
      <div id="reader-settings-data"
        data-font-family="serif"
        data-font-size="18px">
      </div>
      <div id="font-settings-button"></div>
      <div id="fontSettingsModal">
        <select id="fontSizeSelect">
          <option value="14px">14px</option>
          <option value="16px">16px</option>
          <option value="18px">18px</option>
          <option value="20px">20px</option>
        </select>
        <select id="fontFamilySelect"></select>
        <div id="fontPreviewText">Sample text for preview</div>
        <button id="fontSettingsSubmit"></button>
      </div>
    `;

    // Mock the words container
    mockWordsContainer = document.createElement('div');
    (viewport.getWordsContainer as jest.Mock).mockReturnValue(mockWordsContainer);

    // Mock document.head.appendChild for Google Fonts loading
    jest.spyOn(document.head, 'appendChild').mockImplementation(() => document.createElement('link'));

    // Mock CSRF token
    Object.defineProperty(document, 'cookie', {
      writable: true,
      value: 'csrftoken=mock-csrf-token',
    });
  });

  describe('initializeReaderSettings', () => {
    test('should load Google Fonts', () => {
      initializeReaderSettings();

      expect(document.head.appendChild).toHaveBeenCalled();
      const appendedLink = (document.head.appendChild as jest.Mock).mock.calls[0][0];
      expect(appendedLink.rel).toBe('stylesheet');
      expect(appendedLink.href).toContain('fonts.googleapis.com');
    });

    test('should populate font family select with all available fonts', () => {
      initializeReaderSettings();

      const fontSelect = document.getElementById('fontFamilySelect') as HTMLSelectElement;
      expect(fontSelect.options.length).toBeGreaterThan(0);

      // Check that we have system fonts and Google fonts
      const systemFontOptions = Array.from(fontSelect.options).filter(
        option => option.getAttribute('data-font-type') === 'system'
      );
      const googleFontOptions = Array.from(fontSelect.options).filter(
        option => option.getAttribute('data-font-type') === 'google'
      );

      expect(systemFontOptions.length).toBeGreaterThan(0);
      expect(googleFontOptions.length).toBeGreaterThan(0);
    });

    test('should set initial values from reader-settings-data', () => {
      initializeReaderSettings();

      const fontSelect = document.getElementById('fontFamilySelect') as HTMLSelectElement;
      const sizeSelect = document.getElementById('fontSizeSelect') as HTMLSelectElement;
      const previewText = document.getElementById('fontPreviewText') as HTMLElement;

      expect(fontSelect.value).toBe('serif');
      expect(sizeSelect.value).toBe('18px');
      expect(previewText.style.fontFamily).toBe('serif');
    });

    test('should use default values when reader-settings-data is missing', () => {
      // Remove settings data element
      const settingsData = document.getElementById('reader-settings-data');
      if (settingsData) settingsData.remove();

      initializeReaderSettings();

      const fontSelect = document.getElementById('fontFamilySelect') as HTMLSelectElement;
      const sizeSelect = document.getElementById('fontSizeSelect') as HTMLSelectElement;

      // Default values defined in the module
      expect(fontSelect.value).toContain('system');
      expect(sizeSelect.value).toBe('16px');
    });
  });

  describe('initializeReaderEventListeners', () => {
    test('should add click listener to font settings button', () => {
      const button = document.getElementById('font-settings-button');
      const addEventListenerSpy = jest.spyOn(button!, 'addEventListener');

      initializeReaderEventListeners();

      expect(addEventListenerSpy).toHaveBeenCalledWith('click', expect.any(Function));

      // Trigger the click event
      button!.click();

      // Should call showModal
      expect(utils.showModal).toHaveBeenCalledWith('fontSettingsModal');

      addEventListenerSpy.mockRestore();
    });

    test('should add click listener to font settings submit button', () => {
      const submitButton = document.getElementById('fontSettingsSubmit');
      const addEventListenerSpy = jest.spyOn(submitButton!, 'addEventListener');

      initializeReaderEventListeners();

      expect(addEventListenerSpy).toHaveBeenCalledWith('click', expect.any(Function));

      addEventListenerSpy.mockRestore();
    });

    test('should add change listener to font family select', () => {
      const fontSelect = document.getElementById('fontFamilySelect');
      const addEventListenerSpy = jest.spyOn(fontSelect!, 'addEventListener');

      initializeReaderEventListeners();

      expect(addEventListenerSpy).toHaveBeenCalledWith('change', expect.any(Function));

      addEventListenerSpy.mockRestore();
    });
  });

  describe('font settings submission', () => {
    beforeEach(() => {
      // Initialize both settings and event listeners
      initializeReaderSettings();
      initializeReaderEventListeners();
    });

    test('should apply and save settings when submit button is clicked', async () => {
      // Set up select values
      const fontSelect = document.getElementById('fontFamilySelect') as HTMLSelectElement;
      const sizeSelect = document.getElementById('fontSizeSelect') as HTMLSelectElement;

      fontSelect.value = 'sans-serif';
      sizeSelect.value = '20px';

      // Mock fetch for settings save
      fetchMock.mockResponseOnce(JSON.stringify({ success: true }));

      // Mock console.log to prevent output
      jest.spyOn(console, 'log').mockImplementation();

      // Click the submit button
      const submitButton = document.getElementById('fontSettingsSubmit');
      submitButton!.click();

      // Check that styles were applied to words container
      expect(mockWordsContainer.style.fontFamily).toBe('sans-serif');
      expect(mockWordsContainer.style.fontSize).toBe('20px');

      // Wait for async save operation
      await new Promise(resolve => setTimeout(resolve, 0));

      // Check that fetch was called with correct data
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/reader-settings/',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'X-CSRFToken': 'mock-csrf-token'
          })
        })
      );

      // Check that modal was closed
      expect(utils.closeModal).toHaveBeenCalledWith('fontSettingsModal');
    });

    test('should update preview text when font family is changed', () => {
      const fontSelect = document.getElementById('fontFamilySelect') as HTMLSelectElement;
      const previewText = document.getElementById('fontPreviewText') as HTMLElement;

      // Trigger change event with new value
      fontSelect.value = 'monospace';
      fontSelect.dispatchEvent(new Event('change'));

      expect(previewText.style.fontFamily).toBe('monospace');
    });

    test('should handle errors during settings save', async () => {
      // Set up select values
      const fontSelect = document.getElementById('fontFamilySelect') as HTMLSelectElement;
      const sizeSelect = document.getElementById('fontSizeSelect') as HTMLSelectElement;

      fontSelect.value = 'serif';
      sizeSelect.value = '16px';

      // Mock console.error to check for error logging
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      // Mock fetch to return an error
      fetchMock.mockRejectOnce(new Error('Network error'));

      // Click the submit button
      const submitButton = document.getElementById('fontSettingsSubmit');
      submitButton!.click();

      // Wait for async save operation
      await new Promise(resolve => setTimeout(resolve, 0));

      // Check that error was logged
      expect(consoleErrorSpy).toHaveBeenCalled();

      // Modal should not be closed on error
      expect(utils.closeModal).not.toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Google Fonts loading', () => {
    test('should not load Google Fonts again if already loaded', () => {
      // Mock querySelector to simulate an existing font link
      const querySelectorSpy = jest.spyOn(document, 'querySelector');
      querySelectorSpy.mockImplementation((selector) => {
        if (selector === 'link[href*="fonts.googleapis.com"]') {
          // Return a mock element to indicate fonts are already loaded
          return document.createElement('link');
        }
        // For other selectors, use the actual implementation
        return document.querySelector(selector as any);
      });

      const appendChildSpy = jest.spyOn(document.head, 'appendChild');

      initializeReaderSettings();

      // Should not append another link for Google Fonts
      const appendedLinks = (document.head.appendChild as jest.Mock).mock.calls.filter(
        call => call[0]?.href?.includes('fonts.googleapis.com')
      );
      expect(appendedLinks.length).toBe(0);

      querySelectorSpy.mockRestore();
      appendChildSpy.mockRestore();
    });

    test('should handle font loading success', () => {
      // Mock console.log to check for success logging
      const consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();

      initializeReaderSettings();

      // Get the link element that was added
      const appendedLink = (document.head.appendChild as jest.Mock).mock.calls[0][0];

      // Trigger onload event
      appendedLink.onload();

      // Should log success message
      expect(consoleLogSpy).toHaveBeenCalledWith('Google Fonts loaded successfully');

      consoleLogSpy.mockRestore();
    });

    test('should handle font loading error', () => {
      // Mock console.error to check for error logging
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      initializeReaderSettings();

      // Get the link element that was added
      const appendedLink = (document.head.appendChild as jest.Mock).mock.calls[0][0];

      // Trigger onerror event
      appendedLink.onerror(new Error('Font loading failed'));

      // Should log error message
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to load Google Fonts:',
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });
  });
});
