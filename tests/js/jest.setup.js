/**
 * @jest-environment jsdom
 */

global.wordsContainer = document.createElement('div');
global.wordsContainer.id = 'words-container';
document.body.appendChild(global.wordsContainer);
