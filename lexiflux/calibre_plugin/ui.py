"""Calibre plugin UI implementation for Lexiflux."""

import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from calibre.gui2 import (
    I,  # For built-in icons
    error_dialog,
)
from calibre.gui2.actions import InterfaceAction
from calibre.utils.config import JSONConfig
from PyQt5.Qt import (
    QDialog,
    QHBoxLayout,
    QIcon,
    QLabel,
    QPixmap,
    QProgressBar,
    QPushButton,
    QThread,
    QVBoxLayout,
)
from PyQt5.QtCore import pyqtSignal


class UploadThread(QThread):
    """Background thread for uploading books."""

    progress_update = pyqtSignal(str, int, int)  # message, current, total
    upload_complete = pyqtSignal(bool, str)  # success, message

    def __init__(self, book_ids, gui, server_url, api_token):
        super().__init__()
        self.book_ids = book_ids
        self.gui = gui
        self.server_url = server_url
        self.api_token = api_token
        self._stop_requested = False

    def stop(self):
        """Request thread to stop."""
        self._stop_requested = True

    def run(self):
        """Upload books in background."""
        db = self.gui.current_db.new_api
        success_count = 0
        failed_books = []
        total_books = len(self.book_ids)

        for i, book_id in enumerate(self.book_ids):
            if self._stop_requested:
                break

            try:
                metadata = db.get_metadata(book_id)
                formats = db.formats(book_id)

                if not formats:
                    failed_books.append((metadata.title, "No formats available"))
                    continue

                # Try formats in order of preference
                book_format = None
                for fmt in ["EPUB", "HTML", "TXT"]:
                    if fmt in formats:
                        book_format = fmt
                        break

                if not book_format:
                    book_format = list(formats)[0]

                # Get book file path
                book_path = db.format_abspath(book_id, book_format)
                if not book_path or not os.path.exists(book_path):
                    failed_books.append((metadata.title, "File not found"))
                    continue

                title = metadata.title or "Unknown"
                self.progress_update.emit(
                    f"Uploading: {title} ({book_format})",
                    i + 1,
                    total_books,
                )

                # Prepare metadata
                metadata_dict = {
                    "title": metadata.title,
                    "authors": list(metadata.authors or []),
                    "language": str(metadata.language) if metadata.language else "en",
                    "series": metadata.series,
                    "series_index": metadata.series_index,
                    "tags": list(metadata.tags or []),
                    "publisher": metadata.publisher,
                    "published": str(metadata.pubdate) if metadata.pubdate else None,
                    "identifier": metadata.isbn or None,
                }

                # Upload book
                success, error_msg = self.upload_single_book(
                    book_path,
                    metadata_dict,
                    book_format.lower(),
                )

                if success:
                    success_count += 1
                else:
                    failed_books.append((metadata.title, error_msg))

            except Exception as e:
                failed_books.append((f"Book ID {book_id}", str(e)))

        # Prepare final message
        if self._stop_requested:
            message = f"Upload cancelled. Uploaded {success_count} of {total_books} books"
        elif failed_books:
            message = f"Uploaded {success_count} of {total_books} books.\n"
            message += f"Failed: {', '.join(book[0] for book in failed_books[:3])}"
            if len(failed_books) > 3:
                message += f" and {len(failed_books) - 3} more"
        else:
            message = f"Successfully uploaded all {total_books} books"

        self.upload_complete.emit(success_count == total_books, message)

    def upload_single_book(self, book_path, metadata, book_format):
        """Upload a single book to server."""
        try:
            import mimetypes

            url = self.server_url.rstrip("/") + "/calibre/upload/"

            # Read file
            with open(book_path, "rb") as f:
                book_data = f.read()

            # Create multipart form data
            boundary = "----FormBoundary1234567890"
            filename = os.path.basename(book_path)

            # Build form data parts
            parts = []

            # Add metadata field
            parts.append(f"--{boundary}")
            parts.append('Content-Disposition: form-data; name="metadata"')
            parts.append("")
            parts.append(json.dumps(metadata))

            # Add file field
            parts.append(f"--{boundary}")
            parts.append(f'Content-Disposition: form-data; name="book_file"; filename="{filename}"')

            # Determine content type
            content_type = mimetypes.guess_type(book_path)[0] or "application/octet-stream"
            parts.append(f"Content-Type: {content_type}")
            parts.append("")

            # Join text parts
            text_data = "\r\n".join(parts) + "\r\n"

            # Combine with binary data
            body = text_data.encode("utf-8") + book_data + f"\r\n--{boundary}--\r\n".encode()

            # Create request
            headers = {
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            }

            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            req = Request(url, data=body, headers=headers)
            response = urlopen(req, timeout=30)

            if response.status == 200:
                return True, None
            return False, f"Server returned status {response.status}"

        except HTTPError as e:
            return False, f"HTTP Error {e.code}: {e.reason}"
        except Exception as e:
            return False, str(e)


class UploadDialog(QDialog):
    """Dialog for uploading books with progress feedback."""

    def __init__(self, parent, book_ids, server_url, api_token):
        super().__init__(parent)
        self.book_ids = book_ids
        self.server_url = server_url
        self.api_token = api_token
        self.upload_thread = None
        self.setup_ui()

    def setup_ui(self):
        """Initialize dialog UI."""
        self.setWindowTitle("Upload Books to Lexiflux")
        self.setModal(True)
        self.resize(500, 200)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Status label
        self.status_label = QLabel(f"Ready to upload {len(self.book_ids)} book(s)")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Buttons
        button_layout = QHBoxLayout()

        self.upload_button = QPushButton("Start Upload")
        self.upload_button.clicked.connect(self.start_upload)
        button_layout.addWidget(self.upload_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_upload)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def start_upload(self):
        """Start the upload process."""
        self.upload_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.close_button.setEnabled(False)

        self.upload_thread = UploadThread(
            self.book_ids,
            self.parent(),
            self.server_url,
            self.api_token,
        )
        self.upload_thread.progress_update.connect(self.update_progress)
        self.upload_thread.upload_complete.connect(self.upload_finished)
        self.upload_thread.start()

    def cancel_upload(self):
        """Cancel the upload process."""
        if self.upload_thread and self.upload_thread.isRunning():
            self.upload_thread.stop()
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Cancelling...")

    def update_progress(self, message, current, total):
        """Update progress display."""
        self.status_label.setText(message)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{current}/{total} ({current * 100 // total}%)")

    def upload_finished(self, success, message):
        """Handle upload completion."""
        self.status_label.setText(message)
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)

        if success:
            self.upload_button.setText("Upload Complete")
            self.progress_bar.setFormat("Complete")
        else:
            self.upload_button.setText("Retry")
            self.upload_button.setEnabled(True)

    def closeEvent(self, event):
        """Handle dialog close event."""
        if self.upload_thread and self.upload_thread.isRunning():
            event.ignore()
            error_dialog(
                self,
                "Upload in Progress",
                "Please wait for the upload to complete or cancel it first.",
                show=True,
            )


class InterfacePlugin(InterfaceAction):
    """Main plugin interface for Calibre."""

    name = "Send to Lexiflux"

    # Toolbar action specification
    action_spec = (
        "Send to Lexiflux",  # Text
        None,  # Icon (loaded in genesis)
        "Send selected books to Lexiflux server",  # Tooltip
        "Ctrl+Shift+L",  # Keyboard shortcut
    )

    # Plugin behavior
    dont_add_to = frozenset()  # Show in all menus
    action_type = "current"  # Act on selected books
    action_add_menu = True  # Add to menus
    action_menu_clone_qaction = True  # Show in context menu

    def genesis(self):
        """Initialize plugin when loaded."""
        # Try to load icon
        icon = self._get_icon()
        if icon:
            self.qaction.setIcon(icon)

        # Connect action
        self.qaction.triggered.connect(self.send_books)

        # Load settings
        self.load_settings()

    def _get_icon(self):
        """Load plugin icon."""
        try:
            # Try to load from plugin resources
            from calibre_plugins.lexiflux import get_resources

            pixmap = QPixmap()
            pixmap.loadFromData(get_resources("images/icon.png"))
            if not pixmap.isNull():
                return QIcon(pixmap)
        except:
            pass

        # Return default icon
        return QIcon(I("forward.png"))  # Calibre's built-in forward icon

    def location_selected(self, loc):
        """Enable/disable based on current location."""
        # Only enable when viewing library (not device view)
        enabled = loc == "library"
        self.qaction.setEnabled(enabled)

    def load_settings(self):
        """Load plugin settings."""
        prefs = JSONConfig("plugins/lexiflux")
        prefs.defaults["server_url"] = "{{SERVER_URL}}"  # Default from server
        prefs.defaults["api_token"] = ""

        self.server_url = prefs["server_url"]
        self.api_token = prefs["api_token"]

    def apply_settings(self):
        """Apply new settings."""
        self.load_settings()

    def send_books(self):
        """Send selected books to Lexiflux."""
        # Get selected books
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            return error_dialog(
                self.gui,
                "No Selection",
                "Please select one or more books to send to Lexiflux.",
                show=True,
            )

        # Check configuration
        if not self.server_url:
            return error_dialog(
                self.gui,
                "Configuration Required",
                "Please configure the Lexiflux server URL in plugin preferences.",
                show=True,
            )

        # Get book IDs
        book_ids = [self.gui.library_view.model().id(row) for row in rows]

        # Show upload dialog
        dialog = UploadDialog(self.gui, book_ids, self.server_url, self.api_token)
        dialog.exec_()
