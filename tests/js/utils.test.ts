import {
  debugLogging,
  log,
  getElement,
  showModal,
  closeModal
} from '../../lexiflux/viewport/utils';

describe('utils.ts tests', () => {
  // Store original console.log
  const originalConsoleLog = console.log;

  beforeEach(() => {
    // Reset DOM
    document.body.innerHTML = '';

    // Mock console.log
    console.log = jest.fn();
  });

  afterEach(() => {
    // Restore console.log
    console.log = originalConsoleLog;
  });

  describe('log', () => {
    test('should log messages when debugLogging is true', () => {
      // Ensure debugLogging is true
      (debugLogging as any) = true;

      log('test message', 123, { key: 'value' });

      expect(console.log).toHaveBeenCalledWith('test message', 123, { key: 'value' });
    });

    test('should not log messages when debugLogging is false', () => {
      // Set debugLogging to false
      (debugLogging as any) = false;

      log('test message');

      expect(console.log).not.toHaveBeenCalled();
    });
  });

  describe('getElement', () => {
    test('should return the element when it exists', () => {
      // Create test element
      const testDiv = document.createElement('div');
      testDiv.id = 'test-id';
      document.body.appendChild(testDiv);

      const result = getElement('test-id');

      expect(result).toBe(testDiv);
    });

    test('should throw error when element does not exist', () => {
      expect(() => getElement('non-existent-id')).toThrow(
        'Could not find element (id=non-existent-id).'
      );
    });
  });

  describe('showModal', () => {
    test('should show the modal and focus first input', () => {
      // Create modal element with input
      const modal = document.createElement('div');
      modal.id = 'test-modal';
      modal.setAttribute('aria-hidden', 'true');

      const input = document.createElement('input');
      input.type = 'text';
      modal.appendChild(input);

      document.body.appendChild(modal);

      // Mock input.focus
      const focusSpy = jest.spyOn(input, 'focus');

      showModal('test-modal');

      // Check that modal is shown
      expect(modal.classList.contains('show')).toBe(true);
      expect(modal.style.display).toBe('block');
      expect(modal.getAttribute('aria-hidden')).toBeNull();

      // Check that input is focused
      expect(focusSpy).toHaveBeenCalled();

      focusSpy.mockRestore();
    });

    test('should handle modal without input elements', () => {
      // Create modal element without input
      const modal = document.createElement('div');
      modal.id = 'test-modal';
      document.body.appendChild(modal);

      // Should not throw error
      expect(() => showModal('test-modal')).not.toThrow();

      // Check that modal is shown
      expect(modal.classList.contains('show')).toBe(true);
    });

    test('should do nothing if modal does not exist', () => {
      // Call with non-existent modal
      showModal('non-existent-modal');

      // Should not throw error
      expect(true).toBe(true); // Dummy assertion to indicate test passed
    });
  });

  describe('closeModal', () => {
    test('should hide the modal', () => {
      // Create modal element that is shown
      const modal = document.createElement('div');
      modal.id = 'test-modal';
      modal.classList.add('show');
      modal.style.display = 'block';
      document.body.appendChild(modal);

      closeModal('test-modal');

      // Check that modal is hidden
      expect(modal.classList.contains('show')).toBe(false);
      expect(modal.style.display).toBe('none');
      expect(modal.getAttribute('aria-hidden')).toBe('true');
    });

    test('should do nothing if modal does not exist', () => {
      // Call with non-existent modal
      closeModal('non-existent-modal');

      // Should not throw error
      expect(true).toBe(true); // Dummy assertion to indicate test passed
    });
  });
});
