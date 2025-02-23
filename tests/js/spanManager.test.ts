import { TranslationSpanManager, TranslationSpan } from '../../lexiflux/viewport/TranslationSpanManager';

describe('TranslationSpanManager', () => {
  let manager: TranslationSpanManager;

  beforeEach(() => {
    manager = new TranslationSpanManager();
  });

  describe('addSpan', () => {
    test('should add a span and map all words within range', () => {
      manager.addSpan(1, 3);

      expect(manager.getSpan(1)).toEqual({ firstWordId: 1, lastWordId: 3 });
      expect(manager.getSpanForWord(1)).toBe(1);
      expect(manager.getSpanForWord(2)).toBe(1);
      expect(manager.getSpanForWord(3)).toBe(1);
      expect(manager.getSpanForWord(4)).toBeUndefined();
    });

    test('should handle single-word spans', () => {
      manager.addSpan(1, 1);

      expect(manager.getSpan(1)).toEqual({ firstWordId: 1, lastWordId: 1 });
      expect(manager.getSpanForWord(1)).toBe(1);
      expect(manager.getSpanForWord(2)).toBeUndefined();
    });

    test('should overwrite existing spans', () => {
      manager.addSpan(1, 3);
      manager.addSpan(2, 4);

      expect(manager.getSpanForWord(1)).toBe(1);
      expect(manager.getSpanForWord(2)).toBe(2);
      expect(manager.getSpanForWord(3)).toBe(2);
      expect(manager.getSpanForWord(4)).toBe(2);
    });
  });

  describe('removeSpan', () => {
    test('should remove span and all word mappings', () => {
      manager.addSpan(1, 3);
      manager.removeSpan(1);

      expect(manager.getSpan(1)).toBeUndefined();
      expect(manager.getSpanForWord(1)).toBeUndefined();
      expect(manager.getSpanForWord(2)).toBeUndefined();
      expect(manager.getSpanForWord(3)).toBeUndefined();
    });

    test('should handle removing non-existent span', () => {
      manager.removeSpan(999);
      expect(manager.getSpan(999)).toBeUndefined();
    });
  });

  describe('clear', () => {
    test('should remove all spans and mappings', () => {
      manager.addSpan(1, 3);
      manager.addSpan(5, 7);
      manager.clear();

      expect(manager.getSpan(1)).toBeUndefined();
      expect(manager.getSpan(5)).toBeUndefined();
      expect(manager.getSpanForWord(1)).toBeUndefined();
      expect(manager.getSpanForWord(6)).toBeUndefined();
    });
  });

  describe('getAffectedSpans', () => {
    beforeEach(() => {
      // Set up some spans for testing
      manager.addSpan(1, 3);  // Span 1: words 1-3
      manager.addSpan(5, 7);  // Span 2: words 5-7
      manager.addSpan(9, 10); // Span 3: words 9-10
    });

    test('should find spans containing selected words', () => {
      const affected = manager.getAffectedSpans([2, 3]);
      expect(affected).toEqual(new Set([1]));
    });

    test('should find multiple affected spans', () => {
      const affected = manager.getAffectedSpans([3, 5]);
      expect(affected).toEqual(new Set([1, 5]));
    });

    test('should include adjacent spans', () => {
      const affected = manager.getAffectedSpans([4]);
      expect(affected).toEqual(new Set([1, 5])); // Spans adjacent to word 4
    });

    test('should handle words with no spans', () => {
      const affected = manager.getAffectedSpans([15, 16]);
      expect(affected).toEqual(new Set());
    });
  });

  describe('getExtendedWordIds', () => {
    beforeEach(() => {
      manager.addSpan(1, 3);  // Span 1: words 1-3
      manager.addSpan(5, 7);  // Span 2: words 5-7
    });

    test('should include all words from affected spans', () => {
      const extended = manager.getExtendedWordIds([2]);
      expect(extended).toEqual(new Set([1, 2, 3]));
    });

    test('should include words from multiple spans', () => {
      const extended = manager.getExtendedWordIds([3, 5]);
      expect(extended).toEqual(new Set([1, 2, 3, 5, 6, 7]));
    });

    test('should include original words and words from adjacent spans', () => {
      const extended = manager.getExtendedWordIds([4, 5]);
      expect(extended).toEqual(new Set([1, 2, 3, 4, 5, 6, 7]));
    });

    test('should handle words with no spans', () => {
      const extended = manager.getExtendedWordIds([15, 16]);
      expect(extended).toEqual(new Set([15, 16]));
    });
  });
});
