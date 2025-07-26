# Lexiflux Calibre Plugin

This directory contains the Calibre plugin source files for Lexiflux integration.

## File Structure

- `__init__.py` - Plugin metadata and configuration
- `ui.py` - Main plugin UI implementation with upload functionality
- `config.py` - Configuration dialog for plugin settings
- `plugin-import-name-lexiflux.txt` - Empty file required for multi-file plugins
- `images/icon.png` - Plugin icon (optional, 48x48 pixels recommended)

## Building the Plugin

The plugin is automatically packaged when users download it from the Lexiflux web interface. The server URL is dynamically inserted during packaging.

## Development

To test the plugin during development:

1. Create a ZIP file containing all files in this directory
2. Load the ZIP file in Calibre via Preferences → Plugins → Load plugin from file
3. Restart Calibre

## Features

- Upload selected books to Lexiflux server
- Support for EPUB, HTML, and TXT formats
- Progress tracking with cancel support
- Metadata preservation during upload
- Configuration dialog with connection testing
- Keyboard shortcut support (Ctrl+Shift+L)

## Server Integration

The plugin sends books to the `/calibre/upload/` endpoint using multipart form data with:
- `book_file` - The book file content
- `metadata` - JSON metadata including title, authors, language, etc.
