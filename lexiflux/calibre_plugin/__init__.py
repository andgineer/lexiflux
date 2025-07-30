"""Calibre plugin for Lexiflux integration."""

from calibre.customize import InterfaceActionBase


class LexifluxPlugin(InterfaceActionBase):
    """Main plugin class for Calibre integration."""

    name = "Send to Lexiflux"
    description = "Send books to Lexiflux server"
    supported_platforms = ["windows", "osx", "linux"]
    author = "Lexiflux"
    version = (1, 0, 0)
    minimum_calibre_version = (0, 7, 53)

    # Points to the actual UI implementation
    actual_plugin = "calibre_plugins.lexiflux.ui:InterfacePlugin"
    
    # Placeholder replaced in plugin download - do not change even formatting (see constants.py)
    default_prefs = {
        'server_url': 'https://your-lexiflux-server.com',
        'api_token': '',
    }

    def is_customizable(self):
        """Plugin has configuration dialog."""
        return True

    def config_widget(self):
        """Return configuration widget."""
        from calibre_plugins.lexiflux.config import ConfigWidget

        return ConfigWidget()

    def save_settings(self, config_widget):
        """Save configuration settings."""
        config_widget.save_settings()

        # Apply settings to running plugin instance
        ac = self.actual_plugin_
        if ac is not None:
            ac.apply_settings()
