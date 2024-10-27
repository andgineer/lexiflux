import { showModal, closeModal } from './utils';
import { viewport } from './viewport';

export interface ReaderSettings {
    font_size: string;
    font_family: string;
}

interface FontOption {
  name: string;
  value: string;
  type: 'system' | 'google';
}

const SYSTEM_FONTS: FontOption[] = [
  { name: 'System Default', value: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif', type: 'system' },
  { name: 'Serif', value: 'serif', type: 'system' },
  { name: 'Sans-serif', value: 'sans-serif', type: 'system' },
  { name: 'Monospace', value: 'monospace', type: 'system' },
];

const GOOGLE_FONTS: FontOption[] = [
  { name: 'Roboto', value: 'Roboto', type: 'google' },
  { name: 'Open Sans', value: 'Open Sans', type: 'google' },
  { name: 'Noto Sans', value: 'Noto Sans', type: 'google' },
  { name: 'Lato', value: 'Lato', type: 'google' },
];

const ALL_FONTS = [...SYSTEM_FONTS, ...GOOGLE_FONTS];

const DEFAULT_FONT_SIZE = '16px';
const DEFAULT_FONT_FAMILY = SYSTEM_FONTS[0].value;

// Functions
function loadGoogleFonts(): void {
  const link = document.createElement('link');
  link.rel = 'stylesheet';

  const fonts = GOOGLE_FONTS.map(font => font.name.replace(' ', '+')).join('|');
  link.href = `https://fonts.googleapis.com/css2?family=${fonts}&display=swap`;

  document.head.appendChild(link);
}

function applyReaderSettings(settings: ReaderSettings): void {
  const wordsContainer = viewport.getWordsContainer();
  if (wordsContainer) {
    wordsContainer.style.fontSize = settings.font_size;
    wordsContainer.style.fontFamily = settings.font_family;
  }
}

async function saveReaderSettings(settings: ReaderSettings): Promise<void> {
    try {
        const formData = new FormData();
        formData.append('book_code', viewport.bookCode);
        formData.append('font_family', settings.font_family);
        formData.append('font_size', settings.font_size);

        const response = await fetch('/api/reader-settings/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Failed to save reader settings:', errorText);
            throw new Error(errorText);
        }
    } catch (error) {
        console.error('Error saving reader settings:', error);
        throw error;
    }
}

function getCsrfToken(): string {
  const csrfCookie = document.cookie
    .split(';')
    .find(cookie => cookie.trim().startsWith('csrftoken='));
  return csrfCookie ? csrfCookie.split('=')[1] : '';
}

function handleReaderSettingsSubmit(): void {
  const sizeSelect = document.getElementById('fontSizeSelect') as HTMLSelectElement;
  const familySelect = document.getElementById('fontFamilySelect') as HTMLSelectElement;

  if (sizeSelect && familySelect) {
    const newSettings: ReaderSettings = {
      font_size: sizeSelect.value,
      font_family: familySelect.value
    };

    applyReaderSettings(newSettings);
    saveReaderSettings(newSettings);
    closeModal('fontSettingsModal');
  }
}

function handleReaderSettingsButtonClick(event: Event): void {
  event.preventDefault();
  showModal('fontSettingsModal');
}

function handleFontSelectChange(event: Event): void {
  const select = event.target as HTMLSelectElement;
  const previewText = document.getElementById('fontPreviewText');

  if (previewText) {
    previewText.style.fontFamily = select.value;
  }
}

export function initializeReaderSettings(): void {
  loadGoogleFonts();

  const savedSize = DEFAULT_FONT_SIZE;
  const savedFamily = DEFAULT_FONT_FAMILY;

  const sizeSelect = document.getElementById('fontSizeSelect') as HTMLSelectElement;
  const familySelect = document.getElementById('fontFamilySelect') as HTMLSelectElement;

  if (familySelect) {
    // Clear existing options
    familySelect.innerHTML = '';

    // Populate font select with all available options
    ALL_FONTS.forEach(font => {
      const option = document.createElement('option');
      option.value = font.value;
      option.textContent = font.name;
      option.setAttribute('data-font-type', font.type);
      familySelect.appendChild(option);
    });

    familySelect.value = savedFamily;
  }

  if (sizeSelect) sizeSelect.value = savedSize;
}

export function initializeReaderEventListeners(): void {
  let fontSettingsButton = document.getElementById('font-settings-button');
  if (fontSettingsButton) {
    fontSettingsButton.removeEventListener('click', handleReaderSettingsButtonClick);
    fontSettingsButton.addEventListener('click', handleReaderSettingsButtonClick);
  }

  let fontSettingsSubmit = document.getElementById('fontSettingsSubmit');
  if (fontSettingsSubmit) {
    fontSettingsSubmit.removeEventListener('click', handleReaderSettingsSubmit);
    fontSettingsSubmit.addEventListener('click', handleReaderSettingsSubmit);
  }

  let fontFamilySelect = document.getElementById('fontFamilySelect');
  if (fontFamilySelect) {
    fontFamilySelect.removeEventListener('change', handleFontSelectChange);
    fontFamilySelect.addEventListener('change', handleFontSelectChange);
  }
}
