"""Update LexiFlux to the latest released version."""

import os
import re
import shutil
import subprocess
from typing import Any, Tuple

from django.core.management.base import BaseCommand
from django.core.management import call_command
from lexiflux.__about__ import __version__


class Command(BaseCommand):  # type: ignore
    """Update LexiFlux to the latest released version."""

    help = "Update LexiFlux to the latest released version"

    def run_command(self, command: str) -> Tuple[str, str, int]:
        """Run a shell command and return the output, error, and return code."""
        try:
            with subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                text=True,
                encoding="utf-8",
            ) as process:
                output, error = process.communicate()
                return output, error, process.returncode
        except subprocess.SubprocessError as e:
            return "", str(e), 1

    def get_current_version(self) -> str:
        """Get the current version of LexiFlux."""
        return __version__

    def parse_version_str(self, version: str) -> tuple[int, int, int]:
        """Parse a version string into a tuple of integers."""
        return tuple(map(int, version.lstrip("v").split(".")))  # type: ignore

    def handle(self, *args: Any, **options: Any) -> None:  # pylint: disable=too-many-locals
        """Handle the command."""
        self.stdout.write("Checking for LexiFlux updates...")

        current_version = self.get_current_version()
        current_version_tuple = self.parse_version_str(current_version)

        repo_url = "https://github.com/andgineer/lexiflux.git"

        # Fetch tags
        output, error, code = self.run_command(f"git ls-remote --tags {repo_url}")
        if code != 0:
            self.stderr.write(f"Error fetching tags: {error}")
            return

        # Parse tags, filtering out annotated tag references
        tag_pattern = re.compile(r"refs/tags/(v\d+\.\d+\.\d+)$")
        tags = []
        for line in output.splitlines():
            match = tag_pattern.search(line)
            if match:
                tags.append(match.group(1))

        if not tags:
            self.stderr.write("No version tags found in the repository.")
            return

        latest_tag = max(tags, key=self.parse_version_str)
        latest_tag_tuple = self.parse_version_str(latest_tag.lstrip("v"))

        if current_version_tuple == latest_tag_tuple:
            self.stdout.write(
                self.style.SUCCESS(f"Already at the latest released version ({current_version}).")
            )
            return
        if current_version_tuple > latest_tag_tuple:
            self.stderr.write(
                self.style.ERROR(
                    f"Current version ({current_version}) is higher "
                    f"than the latest release ({latest_tag}). Cannot update."
                )
            )
            return

        self.stdout.write(f"Updating from version {current_version} to {latest_tag}")

        temp_dir = "/tmp/lexiflux_update"
        if os.path.exists(temp_dir):
            self.stdout.write(f"Removing existing temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir)

        # Clone the specific tag
        output, error, code = self.run_command(
            f"git clone --depth 1 --branch {latest_tag} {repo_url} {temp_dir}"
        )
        if code != 0:
            self.stderr.write(f"Error cloning repository: {error}")
            return

        # Copy files outside of lexiflux directory
        essential_files = ["manage", "requirements.txt"]
        for file in essential_files:
            shutil.copy2(os.path.join(temp_dir, file), "/lexiflux/")

        # Copy lexiflux directory
        shutil.copytree(
            os.path.join(temp_dir, "lexiflux"), "/lexiflux/lexiflux", dirs_exist_ok=True
        )

        # Clean up
        shutil.rmtree(temp_dir)

        # Update dependencies
        output, error, code = self.run_command("pip install -r requirements.txt")
        if code != 0:
            self.stderr.write(f"Error updating dependencies: {error}")
            return

        # Run database migrations
        call_command("migrate")

        self.stdout.write(self.style.SUCCESS(f"Successfully updated to version {latest_tag}"))

        self.stdout.write(
            self.style.SUCCESS("Please restart the server with `docker restart lexiflux`.")
        )
