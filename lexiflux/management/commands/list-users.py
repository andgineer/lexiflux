"""Management command to list users."""  # noqa: N806

import argparse
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count


class Command(BaseCommand):  # type: ignore
    """List users with optional email filtering and show the number of books owned by each user."""

    help = (
        "List users with optional email filtering and show the number of books owned by each user"
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "email",
            nargs="?",
            default=None,
            help='Filter users by email (wildcards "*" or "%" are allowed)',
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Maximum number of users to display (default: 20)",
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        limit = options["limit"]
        email_filter = options["email"]

        user = get_user_model()

        users = user.objects.annotate(num_owned_books=Count("owned_books"))

        if email_filter:
            # Handle wildcard pattern correctly
            email_filter = email_filter.replace("*", ".*")
            email_filter = email_filter.replace("%", ".*")
            email_filter = f"^{email_filter}$"

            # Apply email filtering using regular expression
            users = users.filter(email__iregex=email_filter)

        total_users = users.count()

        if total_users == 0:
            self.stdout.write(self.style.WARNING("No users found matching the criteria."))
            return

        self.stdout.write(self.style.SUCCESS(f"Total users found: {total_users}"))

        # Limit the number of users to display
        users = users[:limit]

        for user in users:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Username: {user.username}, Email: {user.email}, "
                    f"Number of Books Owned: {user.num_owned_books}",
                ),
            )
