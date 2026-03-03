# AGENTS.md — Wildleague Backend

This file provides guidance for agentic coding agents working in this repository.

---

## Stack Overview

- **Language**: Python 3.11
- **Framework**: Django 5.0.2 + Django REST Framework
- **Database**: PostgreSQL 16
- **Auth**: `djangorestframework-simplejwt`
- **Protocol layer**: ActivityPub (`src/api/ap/`)
- **Game server**: Nakama (Lua modules in `realtime/modules/`)
- **File storage**: SeaweedFS
- **Runtime**: Gunicorn in production; `manage.py runserver` in development

---

## Project Structure

```
backend/
├── manage.py                  # Django CLI entry point
├── requirements.txt           # Pinned Python dependencies
├── docker-compose.yml         # Full service stack
├── Dockerfile
├── src/
│   ├── urls.py                # Root URL conf (admin + v1/)
│   ├── config/
│   │   ├── dev_settings.py
│   │   └── prod_settings.py
│   └── api/                   # Single Django app
│       ├── models.py
│       ├── serializers.py
│       ├── enums.py
│       ├── urls.py
│       ├── views/             # One file per resource
│       │   ├── __init__.py    # Re-exports all views with *
│       │   ├── auth.py
│       │   ├── card.py
│       │   ├── deck.py
│       │   ├── user.py
│       │   ├── user_relation.py
│       │   └── waitlist.py
│       └── ap/                # ActivityPub protocol layer
│           ├── types.py
│           └── activities/
└── realtime/modules/          # Nakama Lua game logic
```

Settings module is selected by the `ENV` environment variable:
- `ENV=production` → `src.config.prod_settings`
- Default → `src.config.dev_settings`

---

## Build, Run & Install

```bash
# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Run development server
python manage.py runserver

# Run with Docker (all services)
docker compose up

# Docker with file-watch hot reload
docker compose up --watch
```

---

## Testing

Django's built-in test runner is used. No external test framework (pytest, etc.) is configured.

```bash
# Run all tests
python manage.py test

# Run tests for the api app only
python manage.py test src.api

# Run a specific TestCase class
python manage.py test src.api.tests.MyTestCase

# Run a single test method
python manage.py test src.api.tests.MyTestCase.test_method_name
```

Tests live in `src/api/tests.py`. When adding new tests, extend `django.test.TestCase`.
Use `APIClient` from `rest_framework.test` for endpoint tests.

---

## Linting & Formatting

No automated linter or formatter (flake8, black, isort, mypy) is currently configured.
Follow the rules below manually. When a linter/formatter is introduced, defer to its output.

**`.editorconfig` enforces:**
- Indentation: **tabs**, tab width 2
- Line endings: LF
- Charset: UTF-8
- Trim trailing whitespace
- Insert final newline

---

## Code Style Guidelines

### Indentation
Use **tabs** (size 2) throughout Python files. Do not use spaces for indentation.

### Imports
Order imports in three groups, separated by a blank line:
1. Standard library
2. Third-party packages (Django, DRF, cryptography, etc.)
3. Internal project imports

For internal imports, prefer **relative imports** within the same app:
```python
# Preferred within src/api/
from ..models import Card, Users
from ..serializers import CardSerializer
```

Use absolute `src.`-prefixed imports only when crossing app/package boundaries:
```python
from src.api.enums import RelationshipType
```

Do not mix both styles in the same file.

### Naming Conventions

| Construct | Convention | Example |
|---|---|---|
| Classes | `PascalCase` | `AuthModelViewSet`, `Follow` |
| Django models | `PascalCase` | `Users`, `DeckCard`, `UsersRelationship` |
| DB table names | `snake_case` via `Meta.db_table` | `'deck_card'`, `'users_relationship'` |
| ViewSets | `<Entity>ModelViewSet` | `CardModelViewSet` |
| Serializers | `<Entity>Serializer` | `DeckCardsSerializer` |
| Enums (class) | `PascalCase` | `RelationshipType`, `ActivityType` |
| Enum values | `PascalCase` (not SCREAMING_SNAKE) | `FriendRequest`, `Follow` |
| Functions/methods | `snake_case` | `accept_friend_request` |
| Variables | `snake_case` | `user_id`, `serialized_deck` |
| URL patterns/actions | `snake_case` | `accept_friend_request/` |
| Files | `snake_case` | `user_relation.py` |

### Models
- Always specify `db_table` in `Meta` using `snake_case`.
- Use `models.TextChoices` for model-level choice fields.
- Use `class MyEnum(str, Enum)` from the standard `enum` module for non-model enums (see `enums.py`).

### ViewSets
- One file per resource under `src/api/views/`.
- Re-export from `views/__init__.py` using `from .<module> import *`.
- Register ViewSets in `src/api/urls.py` via the DRF router.
- Use `@action(detail=True/False, methods=[...])` for custom endpoints.

### Serializers
- Define in `src/api/serializers.py`.
- Use `ModelSerializer` where possible; specify `fields` explicitly (avoid `fields = '__all__'`).

### Type Annotations
No type hints are used in the current codebase. When adding new code, type hints are required.

---

## Error Handling

### Object lookups — always wrap in try/except
```python
try:
    user = Users.objects.get(username=pk)
except Users.DoesNotExist:
    return Response(status=status.HTTP_404_NOT_FOUND)
```

### Serializer validation — use the is_valid pattern
```python
serializer = MySerializer(data=request.data)
if serializer.is_valid():
    serializer.save()
    return Response(status=status.HTTP_201_CREATED)
return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### Manual input validation — return structured error dicts
```python
return Response({'error': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)
```

### Do not leave unguarded `.objects.get()` calls in views.
Every `get()` that can fail with `DoesNotExist` must be wrapped.

### ActivityPub send() calls
Wrap `requests.post()` in try/except to handle network failures gracefully rather than letting them propagate silently.

---

## Common Pitfalls to Avoid

- Do **not** leave `print()` debug statements in committed code.
- Do **not** commit secrets or credentials. `prod_settings.py` and `.env` are gitignored — keep them that way.
- Do **not** use `fields = '__all__'` in serializers.
- Do **not** mix tab and space indentation in the same file.
- Do **not** import with both relative (`..models`) and absolute (`src.api.models`) styles in the same file.

---

## Environment Variables

Key variables (see `.env.example`):
- `ENV` — `production` or unset (dev)
- `DJANGO_SETTINGS_MODULE` — override settings module
- `SECRET_KEY` — Django secret key
- `DATABASE_URL` or individual `DB_*` vars — PostgreSQL connection
- `NAKAMA_*` — Nakama server connection details

---

## ActivityPub Layer (`src/api/ap/`)

- Activity types are defined as `str, Enum` in `ap/types.py`.
- Each activity (`Follow`, `Accept`, `Reject`) is its own class in `ap/activities/`.
- Each activity class exposes a `send()` method that performs an HTTP POST.
- Use relative imports within the `ap/` package (`from ..types import ActivityType`).
