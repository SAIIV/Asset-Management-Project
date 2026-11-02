from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model (Design Document Section 9, table User).

    Created in Step 1 so that every table that points at a user points at
    this one. Its fields (department, email rules, roles) are added in Step 3.
    """
