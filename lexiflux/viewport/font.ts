import { showModal, closeModal } from './utils';
import { viewport } from './viewport';

// Interfaces
export interface FontSettings {
  size: string;
  family: string;
}

interface FontOption {
  name: string;
  value: string;
  type: 'system' | 'google';
}

// Constants
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

function applyFontSettings(settings: FontSettings): void {
  const wordsContainer = viewport.getWordsContainer();
  if (wordsContainer) {
    wordsContainer.style.fontSize = settings.size;
    wordsContainer.style.fontFamily = settings.family;
  }
}

function handleFontSettingsSubmit(): void {
  const sizeSelect = document.getElementById('fontSizeSelect') as HTMLSelectElement;
  const familySelect = document.getElementById('fontFamilySelect') as HTMLSelectElement;

  if (sizeSelect && familySelect) {
    const newSettings: FontSettings = {
      size: sizeSelect.value,
      family: familySelect.value
    };

    applyFontSettings(newSettings);
//     savePreference('fontSize', newSettings.size);
//     savePreference('fontFamily', newSettings.family);
    closeModal('fontSettingsModal');
  }
}

function handleFontSettingsButtonClick(event: Event): void {
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

export function initializeFontSettings(): void {
  loadGoogleFonts();

  const savedSize = DEFAULT_FONT_SIZE;  //loadPreference('fontSize') || DEFAULT_FONT_SIZE;
  const savedFamily = DEFAULT_FONT_FAMILY; //loadPreference('fontFamily') || DEFAULT_FONT_FAMILY;

  applyFontSettings({ size: savedSize, family: savedFamily });

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

export function initializeFontEventListeners(): void {
  let fontSettingsButton = document.getElementById('font-settings-button');
  if (fontSettingsButton) {
    fontSettingsButton.removeEventListener('click', handleFontSettingsButtonClick);
    fontSettingsButton.addEventListener('click', handleFontSettingsButtonClick);
  }

  let fontSettingsSubmit = document.getElementById('fontSettingsSubmit');
  if (fontSettingsSubmit) {
    fontSettingsSubmit.removeEventListener('click', handleFontSettingsSubmit);
    fontSettingsSubmit.addEventListener('click', handleFontSettingsSubmit);
  }

  let fontFamilySelect = document.getElementById('fontFamilySelect');
  if (fontFamilySelect) {
    fontFamilySelect.removeEventListener('change', handleFontSelectChange);
    fontFamilySelect.addEventListener('change', handleFontSelectChange);
  }
}
