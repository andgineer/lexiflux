export interface ArticleStreamEvent {
  event: 'delta' | 'replace' | 'error' | 'site' | 'done';
  text?: string;
  html?: string;
  kind?: string;
  url?: string;
  window?: boolean;
}

export interface ChunkReader {
  read(): Promise<{ done: boolean; value?: Uint8Array }>;
}

export const CUT_OFF_ERROR = 'cut_off';

export async function readNdjson(
  reader: ChunkReader,
  onEvent: (event: ArticleStreamEvent) => void,
): Promise<void> {
  const decoder = new TextDecoder();
  let pending = '';
  for (;;) {
    const { done, value } = await reader.read();
    pending += done ? decoder.decode() : decoder.decode(value, { stream: true });
    const lines = pending.split('\n');
    pending = done ? '' : (lines.pop() as string);
    for (const line of lines) {
      if (line.trim()) {
        onEvent(JSON.parse(line) as ArticleStreamEvent);
      }
    }
    if (done) {
      return;
    }
  }
}

export function markdownEmphasis(text: string): string {
  return text
    .replace(/\*\*(?=\S)([^\n]*?\S)\*\*/g, '<b>$1</b>')
    // A star followed by a space is a list bullet, not emphasis.
    .replace(/(^|[^*\w])\*([^\s*](?:[^*\n]*?[^\s*])?)\*(?![*\w])/g, '$1<i>$2</i>');
}

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
