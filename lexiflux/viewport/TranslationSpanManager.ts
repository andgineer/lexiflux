export interface TranslationSpan {
  firstWordId: number;
  lastWordId: number;
}

export class TranslationSpanManager {
  private wordToSpanMap: Map<number, number> = new Map();
  private translationSpans: Map<number, TranslationSpan> = new Map();

  clear(): void {
    this.wordToSpanMap.clear();
    this.translationSpans.clear();
  }

  addSpan(firstWordId: number, lastWordId: number): void {
    for (let i = firstWordId; i <= lastWordId; i++) {
      this.wordToSpanMap.set(i, firstWordId);
    }
    this.translationSpans.set(firstWordId, { firstWordId, lastWordId });
  }

  removeSpan(spanId: number): void {
    const span = this.translationSpans.get(spanId);
    if (span) {
      for (let i = span.firstWordId; i <= span.lastWordId; i++) {
        this.wordToSpanMap.delete(i);
      }
      this.translationSpans.delete(spanId);
    }
  }

  getSpanForWord(wordId: number): number | undefined {
    return this.wordToSpanMap.get(wordId);
  }

  getSpan(spanId: number): TranslationSpan | undefined {
    return this.translationSpans.get(spanId);
  }

  getAffectedSpans(wordIds: number[]): Set<number> {
    const affectedSpans = new Set<number>();
    wordIds.forEach(id => {
      const spanId = this.wordToSpanMap.get(id);
      if (spanId !== undefined) {
        affectedSpans.add(spanId);
      }
    });

    // Add adjacent spans
    const minWordId = Math.min(...wordIds);
    const maxWordId = Math.max(...wordIds);

    // Check for adjacent span before the first word
    const beforeSpanId = this.wordToSpanMap.get(minWordId - 1);
    if (beforeSpanId !== undefined) {
      affectedSpans.add(beforeSpanId);
    }

    // Check for adjacent span after the last word
    const afterSpanId = this.wordToSpanMap.get(maxWordId + 1);
    if (afterSpanId !== undefined) {
      affectedSpans.add(afterSpanId);
    }

    return affectedSpans;
  }

  getExtendedWordIds(wordIds: number[]): Set<number> {
    const extendedWordIds = new Set<number>(wordIds);
    const affectedSpans = this.getAffectedSpans(wordIds);

    affectedSpans.forEach(spanId => {
      const span = this.translationSpans.get(spanId);
      if (span) {
        for (let i = span.firstWordId; i <= span.lastWordId; i++) {
          extendedWordIds.add(i);
        }
      }
    });

    return extendedWordIds;
  }
}

export const spanManager = new TranslationSpanManager();
