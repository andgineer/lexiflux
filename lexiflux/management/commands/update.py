"""Update LexiFlux to the latest released version."""

import os
import re
import shutil
import subprocess
import signal
import time
from typing import Any, Tuple
from urllib.request import urlopen
from urllib.error import URLError

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.core.management.base import CommandError
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

    def find_server_pids(self) -> list[int]:
        """Find the PIDs of the running Django server processes."""
        output, _, _ = self.run_command("ps aux | grep '[p]ython.*runserver' | awk '{print $2}'")
        return [int(pid) for pid in output.split()]

    def stop_server(self) -> None:
        """Stop the running Django server processes."""
        pids = self.find_server_pids()
        if pids:
            self.stdout.write(f"Stopping the server (PIDs: {', '.join(map(str, pids))})...")
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass  # Process already terminated
            time.sleep(5)  # Give processes time to shut down gracefully

            # Check if any processes are still running
            remaining_pids = self.find_server_pids()
            if remaining_pids:
                self.stdout.write(
                    "Forcefully terminating remaining processes: "
                    f"{', '.join(map(str, remaining_pids))}"
                )
                for pid in remaining_pids:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        else:
            self.stdout.write("No running server processes found.")

    def start_server(self) -> None:
        """Start the Django server and verify it's running."""
        self.stdout.write("Starting the server...")

        with subprocess.Popen(
            ["python", "manage.py", "runserver", "0.0.0.0:8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as process:
            start_time = time.time()
            while time.time() - start_time < 30:
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    raise CommandError(f"Server failed to start. Error: \n{stderr}\n{stdout}")

                try:
                    with urlopen("http://localhost:8000", timeout=1) as response:
                        if response.status == 200:
                            self.stdout.write(self.style.SUCCESS("Server started successfully."))
                            return
                except URLError:
                    # Server not ready yet, continue waiting
                    pass

                time.sleep(1)

            # If we've reached here, the server didn't start in time
            process.terminate()
            try:
                process.wait(timeout=5)  # Give it 5 seconds to terminate gracefully
            except subprocess.TimeoutExpired:
                process.kill()  # Force kill if it doesn't terminate
            raise CommandError("Server failed to start within the timeout period.")

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
        tag_pattern = re.compile(r"refs/tags/v(\d+\.\d+\.\d+)$")
        tags = []
        for line in output.splitlines():
            match = tag_pattern.search(line)
            if match:
                tags.append(match.group(1))

        if not tags:
            self.stderr.write("No version tags found in the repository.")
            return

        latest_tag = max(tags, key=self.parse_version_str)
        latest_tag_tuple = self.parse_version_str(latest_tag)

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

        # Stop the server
        self.stop_server()

        temp_dir = "/tmp/lexiflux_update"

        # Clone the specific tag
        output, error, code = self.run_command(
            f"git clone --depth 1 --branch {latest_tag} {repo_url} {temp_dir}"
        )
        if code != 0:
            self.stderr.write(f"Error cloning repository: {error}")
            return

        # Copy only essential files
        essential_files = ["manage", "requirements.txt", "__about__.py"]
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

        # Start the server
        self.start_server()

        self.stdout.write(
            self.style.SUCCESS("Update completed successfully and server restarted!")
        )
