"""Configuration dialog for Lexiflux Calibre plugin."""

from calibre.utils.config import JSONConfig
from PyQt5.Qt import QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class ConfigWidget(QWidget):
    """Configuration widget for plugin settings."""

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.initialize()

    def setup_ui(self):
        """Create configuration UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Server settings group
        server_group = QGroupBox("Server Settings")
        server_layout = QVBoxLayout()
        server_group.setLayout(server_layout)

        # Server URL
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Server URL:"))
        self.server_url = QLineEdit()
        self.server_url.setPlaceholderText("https://your-lexiflux-server.com")
        url_layout.addWidget(self.server_url)
        server_layout.addLayout(url_layout)

        # API Token (optional)
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("API Token:"))
        self.api_token = QLineEdit()
        self.api_token.setPlaceholderText("Optional - Leave empty if not required")
        self.api_token.setEchoMode(QLineEdit.Password)
        token_layout.addWidget(self.api_token)
        server_layout.addLayout(token_layout)

        layout.addWidget(server_group)

        # Help text
        help_text = QLabel(
            "Enter the URL of your Lexiflux server.\n"
            "The plugin will send books to: <server_url>/calibre/upload/\n"
            "API token is optional and only needed if your server requires authentication.",
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # Test connection button
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        layout.addWidget(self.test_button)

        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Add stretch to push everything to the top
        layout.addStretch()

    def initialize(self):
        """Load current settings."""
        prefs = JSONConfig("plugins/lexiflux")
        self.server_url.setText(prefs.get("server_url", ""))
        self.api_token.setText(prefs.get("api_token", ""))

    def save_settings(self):
        """Save settings to config."""
        prefs = JSONConfig("plugins/lexiflux")

        # Clean and validate URL
        url = self.server_url.text().strip()
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url

        prefs["server_url"] = url
        prefs["api_token"] = self.api_token.text().strip()

    def test_connection(self):
        """Test connection to server."""
        from urllib.error import HTTPError, URLError
        from urllib.request import Request, urlopen

        url = self.server_url.text().strip()
        if not url:
            self.status_label.setText("❌ Please enter a server URL")
            return

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # Try to connect to the status endpoint
        status_url = url.rstrip("/") + "/calibre/status/"

        self.status_label.setText("Testing connection...")
        self.test_button.setEnabled(False)

        try:
            headers = {}
            token = self.api_token.text().strip()
            if token:
                headers["Authorization"] = f"Bearer {token}"

            req = Request(status_url, headers=headers)
            response = urlopen(req, timeout=10)

            if response.status == 200:
                self.status_label.setText("✅ Connection successful!")
            else:
                self.status_label.setText(f"⚠️ Server returned status {response.status}")

        except HTTPError as e:
            if e.code == 401:
                self.status_label.setText("❌ Authentication failed - check API token")
            else:
                self.status_label.setText(f"❌ HTTP Error {e.code}: {e.reason}")
        except URLError as e:
            self.status_label.setText(f"❌ Connection failed: {str(e.reason)}")
        except Exception as e:
            self.status_label.setText(f"❌ Error: {str(e)}")
        finally:
            self.test_button.setEnabled(True)
