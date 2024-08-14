## Installation

## Backup
To create archive with full backup of your Lexiflux Docker container.

=== "Linux/macOS"
    Enter in the terminal:

    ```bash
    docker commit lexiflux lexiflux_backup
    docker save lexiflux_backup | gzip > lexiflux_backup.tar.gz
    ```

=== "Windows (PowerShell)"
    In the command prompt, type:
    
    ```bash
    docker commit lexiflux lexiflux_backup
    docker save lexiflux_backup -o lexiflux_backup.tar
    ```
