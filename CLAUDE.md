# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Environment
- `uv` is used for Python package management - **NEVER use plain pip, always use uv**
- `. ./activate.sh` or `source ./activate.sh` - Set up development environment (note the space between . and ./activate.sh)
- **IMPORTANT**: Always use `source ./activate.sh` in the same shell session when running commands like pytest, not separate tool calls
- `invoke init-db` - Initialize development database with sample data
- `invoke buildjs` - Build TypeScript frontend assets using webpack
- `invoke reqs` - Update requirements and install dependencies

### Running the Application
- `invoke run` - Run development server with auto-login (localhost:8000)
- `invoke runssl` - Run with SSL for local development
- `invoke runcloud` - Run in multi-user mode
- `invoke shell` - Django shell
- `invoke jupyter` - Run Jupyter notebook with Django shell_plus

### Testing and Quality
- `invoke test` - Run Python tests with pytest and generate Allure report
- `invoke selenium` - Run Selenium end-to-end tests
- `invoke pre` - Run pre-commit hooks (formatting, linting)
- `npm test` - Run JavaScript/TypeScript tests with Jest
- `npm run build` - Build frontend bundle

### Database Operations
- `invoke migrate` - Run Django migrations
- `invoke kill_db` - Reset database
- `invoke admin` - Create admin user (admin/admin)
- `invoke user` - Create default auto-login user

### Book Import Commands
- `./manage import-epub <file_path>` - Import EPUB file
- `./manage import-html <file_path>` - Import HTML file
- `./manage import-text <file_path>` - Import plain text file
- `./manage import-url <url>` - Import web page from URL with image support
  - `--cleaning-level {aggressive,moderate,minimal}` - Content cleaning level
  - `--public` - Make book public
  - `--language <lang>` - Force language detection
  - Automatically downloads and stores images from the web page
  - Updates image URLs to use Django's serve_book_image view

## Architecture Overview

### Backend (Django)
- **Main App**: `lexiflux/` - Django application with models, views, and business logic
- **Models**: Core entities include Book, BookPage, Language, CustomUser, ReadingLoc, TranslationHistory
- **Views**: Organized by feature in `lexiflux/views/` (reader, library, auth, language preferences, etc.)
- **Language Processing**: `lexiflux/language/` - Text processing, translation, and NLP features
- **Book Import**: `lexiflux/ebook/` - Support for EPUB, HTML, plain text, and URL imports
- **AI Integration**: LangChain-based chat models (OpenAI, Anthropic, Google, Mistral, Ollama)

### Frontend Architecture
- **TypeScript**: Main entry point is `lexiflux/viewport/main.ts`
- **Webpack**: Bundles TypeScript to `lexiflux/static/lexiflux/bundle.js`
- **Vue.js**: Used for interactive components (language preferences, AI settings, etc.)
- **Bootstrap**: UI framework with HTMX for dynamic interactions
- **Core Modules**:
  - `viewport.ts` - Text rendering and reading position management
  - `translate.ts` - Translation requests and lexical analysis
  - `readerSettings.ts` - Font and display preferences
  - `TranslationSpanManager.ts` - Manages translation overlays

### Key Features
- **Multi-format Book Reading**: EPUB, HTML, plain text, web pages with full image support
- **Real-time Translation**: Click-to-translate with multiple AI models
- **Language Learning**: Vocabulary tracking, Anki export, lexical analysis
- **Reading Progress**: Position tracking, bookmarks, reading history
- **Multi-language Support**: Interface and content in multiple languages
- **Image Handling**: Automatic download and storage of images from web imports

### Database Design
- SQLite for development, configurable for production
- Custom user model with language preferences
- Book content stored as pages with word-level indexing
- Translation history and vocabulary tracking
- Reading position persistence with word-level accuracy

### Testing Strategy
- **Python Tests**: pytest with Django integration, coverage reporting
- **JavaScript Tests**: Jest with DOM testing utilities
- **E2E Tests**: Selenium with page object pattern
- **Test Data**: Sample books and fixtures in `tests/resources/`
- **CI/CD**: GitHub Actions with Allure reporting

### Development Patterns
- Use `@smart_login_required` decorator for authentication
- Follow Django REST patterns for API endpoints
- TypeScript interfaces for type safety
- Vue.js for complex interactive forms
- HTMX for server-side rendered dynamic content
- Images stored as BLOBs in BookImage model, served via serve_book_image view
- URL imports automatically download and rewrite image references

### Configuration
- **Environment-based settings**: `lexiflux/environments/` with auto-detection via `LEXIFLUX_ENV`
  - `local` - Local development with SQLite and auto-login
  - `docker` - Local Docker with SQLite and simplified static serving
  - `koyeb` - Production deployment with PostgreSQL
- AI model configurations in `lexiflux/resources/chat_models.yaml`
- Translation prompts in `lexiflux/resources/prompts/`
- Docker support with compose file for services (docker-compose.yaml for Selenium tests only)
- Separate docker-compose.postgres.yaml for PostgreSQL debugging (not for regular tests)

## Important Notes
- Auto-login is enabled in development via `LEXIFLUX_SKIP_AUTH=true`
- SSL certificates can be generated with `invoke keygen` or `invoke mkcert`
- Webpack preserves `goToPage` function name for HTML integration
- Vue.js components use `[[]]` delimiters to avoid Django template conflicts
- **ALL documentation and code comments MUST be in English** - this is a strict project requirement

## CRITICAL KOYEB ENVIRONMENT RULES
1. **NEVER use the main .venv environment** (activated by activate.sh) for koyeb testing
2. **ALWAYS use separate .venv-koyeb environment** for koyeb dependencies and testing
3. **NEVER use plain pip** - ALWAYS use `uv pip` (even in .venv-koyeb environment)
4. **Koyeb testing pattern**: `source .venv-koyeb/bin/activate && uv pip install ...` (NOT pip install)
