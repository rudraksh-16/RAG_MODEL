# CODING_REGULATIONS.md — Python Project Coding Standards

> This document defines the **complete, enforceable coding standards** for this project.
> Every rule here is **mandatory**. Deviation is a defect, not a style choice.
> Reference this file during implementation, code review, and refactoring.

---

## TABLE OF CONTENTS

1. [Modularization](#1-modularization)
2. [OOP Concepts](#2-oop-concepts)
3. [DRY — Don't Repeat Yourself](#3-dry--dont-repeat-yourself)
4. [No Dead Code](#4-no-dead-code)
5. [Strict Consistency](#5-strict-consistency)
6. [Import Discipline](#6-import-discipline)
7. [State Management](#7-state-management)
8. [No Tightly Coupled Logic](#8-no-tightly-coupled-logic)
9. [No Responsibility Overload](#9-no-responsibility-overload)
10. [Function Standards](#10-function-standards)

---

## 1. Modularization

**Principle:** Every unit of code must have a single, well-defined purpose and live in the correct module.

### Rules

- **One concern per module.** A `.py` file should contain one cohesive responsibility — not a mix of unrelated classes or utilities.
- **Group by feature, not by type.** Prefer `features/auth/` over scattering `auth_helper.py`, `auth_utils.py` across the root.
- **Shared utilities go in `utils/` or `common/`.** If two features need the same function, it belongs in a shared layer — not copied into both.
- **No god modules.** A file exceeding ~200 lines is a strong signal it needs to be split.
- **Use `__init__.py` as a clean public interface.** Expose only what consumers need. Keep internals private.
- **Package structure must reflect domain boundaries**, not implementation details.

### Folder Structure Example

```
project/
├── features/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── service.py        ← business logic
│   │   ├── repository.py     ← data access
│   │   ├── models.py         ← data models
│   │   └── validators.py     ← input validation
│   └── orders/
│       ├── __init__.py
│       ├── service.py
│       └── repository.py
├── shared/
│   ├── utils/
│   ├── exceptions.py
│   └── constants.py
├── config/
│   └── settings.py
└── main.py
```

### ✅ Correct
```python
# features/auth/service.py — one responsibility: auth business logic
from features.auth.repository import UserRepository
from shared.utils.hashing import hash_password

class AuthService:
    def __init__(self, repository: UserRepository):
        self._repository = repository

    def register_user(self, email: str, password: str) -> None:
        hashed = hash_password(password)
        self._repository.save_user(email, hashed)
```

### ❌ Wrong
```python
# utils.py — dumping ground for everything
def hash_password(): ...
def send_email(): ...
def calculate_tax(): ...
def render_template(): ...
def connect_to_database(): ...
```

---

## 2. OOP Concepts

**Principle:** Follow SOLID principles strictly. Prefer composition over inheritance.

### Rules

- **Single Responsibility (SRP):** Each class manages one domain concept only.
- **Open/Closed (OCP):** Classes should be extendable without modifying existing code. Use abstract base classes and interfaces.
- **Liskov Substitution (LSP):** Subclasses must be fully substitutable for their parent without altering expected behavior.
- **Interface Segregation (ISP):** Use `ABC` and small focused abstract classes. Do not force classes to implement methods they don't need.
- **Dependency Inversion (DIP):** Depend on abstractions, not concrete implementations. Inject dependencies — never instantiate them inside class bodies.
- **No instantiation of dependencies inside `__init__` or methods.** Use constructor injection.
- **Prefer composition over inheritance** for code reuse. Inheritance is only for true "is-a" relationships.
- **Use `@dataclass` or `NamedTuple` for data containers** — do not write classes that are just bags of fields with no behavior.
- **Use `@property`** to expose computed attributes cleanly instead of getter methods.
- **Use `__slots__`** in performance-critical data classes to reduce memory overhead.

### ✅ Correct
```python
from abc import ABC, abstractmethod

class NotificationSender(ABC):
    @abstractmethod
    def send(self, recipient: str, message: str) -> None:
        ...

class EmailSender(NotificationSender):
    def send(self, recipient: str, message: str) -> None:
        # send email implementation
        ...

class NotificationService:
    def __init__(self, sender: NotificationSender) -> None:
        self._sender = sender  # injected abstraction, not a concrete class

    def notify_user(self, user_email: str, message: str) -> None:
        self._sender.send(user_email, message)
```

### ❌ Wrong
```python
class NotificationService:
    def __init__(self):
        self._sender = EmailSender()  # tightly coupled to concrete class

    def notify_user(self, email, message):
        self._sender.send(email, message)

    def format_message(self, msg):   # not this class's responsibility
        return msg.strip().title()

    def log_notification(self, msg): # not this class's responsibility
        print(f"Sent: {msg}")
```

---

## 3. DRY — Don't Repeat Yourself

**Principle:** Every piece of logic, data, or configuration must exist in exactly one place.

### Rules

- **If you write it twice, extract it.** Any logic appearing more than once must be abstracted into a shared function, class method, or constant.
- **Constants are defined once** in `shared/constants.py` or a feature-level `constants.py`. Never repeat a string literal or magic number inline.
- **Shared data models are defined once.** Never re-declare the same dataclass or TypedDict in multiple modules.
- **Validation logic is defined once.** Centralize validators — never duplicate field-level checks across multiple services.

### ✅ Correct
```python
# shared/constants.py
MAX_LOGIN_ATTEMPTS = 5
DEFAULT_PAGE_SIZE = 20
API_TIMEOUT_SECONDS = 30

# used everywhere by name — never as a raw number inline
```

### ❌ Wrong
```python
# service_a.py
if attempts > 5:  # magic number

# service_b.py
for _ in range(5):  # same magic number, different file

# validator.py
if len(results) > 20:  # same magic number, third file
```

---

## 4. No Dead Code

**Principle:** The codebase contains only code that is actively executed and needed.

### Rules

- **Remove unused imports immediately.** Run `autoflake` or check with `flake8` — no unused imports in committed code.
- **Remove unused variables, functions, and parameters.** Prefix intentionally unused variables with `_` (e.g., `_unused`). All others must be removed.
- **No commented-out code.** Use version control (`git`) for history — not inline comments.
- **No `print()` statements in committed code.** Use the `logging` module exclusively.
- **No TODO comments that refer to known, shippable work.** TODOs must reference a ticket or be resolved before merge.
- **No unreachable code paths.** Dead `if/else` branches and impossible conditions must be removed.
- **No empty `except` blocks.** Every `except` must handle or re-raise — never silently swallow exceptions.

### ✅ Correct
```python
import logging
from features.auth.service import AuthService

logger = logging.getLogger(__name__)
```

### ❌ Wrong
```python
import logging
import os          # unused
import json        # unused
from features.auth.service import AuthService
from features.auth.utils import hash_password  # unused

# print("debug check")   # commented-out debug

def old_register_user(email):  # dead function, never called
    pass
```

---

## 5. Strict Consistency

**Principle:** The entire project must look and behave as if written by one person.

### Rules

- **Pick one convention at project start — never deviate.**
- **Follow PEP 8** as the baseline. Use `black` for formatting and `flake8`/`pylint` for linting.
- **Use type hints on every function signature.** No exceptions.

### Naming Conventions

| Entity | Convention | Example |
|---|---|---|
| Modules / files | `snake_case` | `user_service.py` |
| Classes | `PascalCase` | `UserService`, `OrderRepository` |
| Functions & methods | `snake_case` | `get_user_by_id`, `calculate_total` |
| Variables | `snake_case` | `user_count`, `is_active` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `API_BASE_URL` |
| Private attributes | `_single_underscore` | `self._repository` |
| Name-mangled attributes | `__double_underscore` | `self.__secret` (use sparingly) |
| Type aliases | `PascalCase` | `UserId = int` |
| Abstract base classes | `PascalCase` | `BaseRepository`, `AbstractSender` |

- **Consistent error handling pattern.** If you use `try/except` with specific exception types in one service — do it everywhere.
- **Consistent async pattern.** Use `async/await` throughout async code. Never mix with callbacks or `concurrent.futures` in the same layer.
- **Consistent return types.** A function always returns the same type. Never `str | None | dict` across different branches unless explicitly typed as `Optional`.
- **Docstrings on every public class and function** using the same format (Google style, NumPy style, or reStructuredText — pick one).

### Docstring Style (Google — pick one and enforce it)
```python
def fetch_user_by_id(user_id: int) -> User:
    """Fetch a single user record by their unique identifier.

    Args:
        user_id: The unique integer ID of the user.

    Returns:
        A User dataclass instance with all fields populated.

    Raises:
        UserNotFoundError: If no user exists with the given ID.
    """
```

---

## 6. Import Discipline

**Principle:** Imports are declarations. They must be at the top, ordered, and minimal.

### Rules

- **All imports at the very top of the file.** No imports inside functions, classes, or conditional blocks unless lazy-loading is explicitly the goal (and must be documented).
- **Import order (PEP 8, enforced by `isort`):**
  1. Standard library imports
  2. Third-party library imports
  3. Local / project imports
  4. Blank line between each group

- **Import specific names, not modules wholesale**, unless the module itself is the interface (e.g., `import os`).
- **Never use wildcard imports** (`from module import *`). They pollute the namespace and make dependency tracking impossible.
- **Alias only when necessary** and use a consistent alias throughout the project (e.g., `import numpy as np` — always `np`, never `numpy` inline and `np` elsewhere).

### ✅ Correct
```python
import logging
import os
from typing import Optional

import httpx
from pydantic import BaseModel

from features.auth.models import User
from shared.constants import API_TIMEOUT_SECONDS
from shared.exceptions import UserNotFoundError
```

### ❌ Wrong
```python
from features.auth.models import *   # wildcard — forbidden
import httpx
import logging
from shared.constants import API_TIMEOUT_SECONDS
import os                            # standard lib mixed into third-party group

def get_user(user_id):
    import json                      # import inside function — forbidden
    ...
```

---

## 7. State Management

**Principle:** State must be minimal, predictable, correctly scoped, and never duplicated.

### Rules

- **Avoid global mutable state.** Module-level variables that change at runtime are bugs waiting to happen. Use dependency injection and instance attributes instead.
- **Class instance state only for things that belong to the object's lifetime.** Transient computation results must not be stored as `self` attributes — return them.
- **Single source of truth.** The same data must never exist in two places. If a value is derivable from another, compute it — don't store it separately.
- **Use `@dataclass(frozen=True)` for immutable value objects.** Prefer immutability wherever state does not need to change.
- **Separate persistent state (database, cache) from in-memory state (service instances, computed values).** Never treat them the same way.
- **All stateful operations must handle all phases:** pending → processing → success → error. Never leave error or failure states unhandled.
- **Configuration is loaded once at startup** from `settings.py` or environment — not re-read on every call.

### ✅ Correct
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Money:
    amount: float
    currency: str

    @property
    def in_cents(self) -> int:
        return int(self.amount * 100)   # derived — not stored
```

### ❌ Wrong
```python
class Money:
    def __init__(self, amount, currency):
        self.amount = amount
        self.currency = currency
        self.in_cents = int(amount * 100)   # stored derived value — duplicated state
        self.formatted = f"{amount} {currency}"  # duplicated again
```

---

## 8. No Tightly Coupled Logic

**Principle:** Modules must be independent enough to change, test, or replace in isolation.

### Rules

- **Depend on abstractions.** Functions and classes receive dependencies as parameters — never import and instantiate them internally.
- **No cross-feature direct internal imports.** Feature A must not import from Feature B's internal modules. Cross-feature communication goes through a shared interface, service layer, or event system.
- **Services must not know about I/O presentation.** A service function must never `print()`, write to HTTP responses, or format display strings.
- **Repositories must not contain business logic.** They fetch and persist data only.
- **No circular imports.** Module A importing Module B which imports Module A is forbidden. Restructure to break the cycle.
- **Use dependency injection** — pass collaborators into constructors, never instantiate them inside methods.

### ✅ Correct
```python
# features/orders/service.py
from features.orders.repository import OrderRepository  # depends on abstraction
from shared.exceptions import OrderNotFoundError

class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    def get_order(self, order_id: int):
        order = self._repository.find_by_id(order_id)
        if not order:
            raise OrderNotFoundError(order_id)
        return order
```

### ❌ Wrong
```python
# features/orders/service.py
import psycopg2   # service directly depends on DB driver

class OrderService:
    def get_order(self, order_id: int):
        conn = psycopg2.connect(...)   # infrastructure detail inside business logic
        cursor = conn.execute(f"SELECT * FROM orders WHERE id = {order_id}")
        print(cursor.fetchone())       # presentation inside service
```

---

## 9. No Responsibility Overload

**Principle:** Nothing should do more than one job. Split early, merge never.

### Rules

- **Services handle business logic only.** No SQL, no HTTP calls, no formatting.
- **Repositories handle data access only.** No business rules, no validation.
- **Validators handle input validation only.** No persistence, no transformation.
- **Utils are pure functions only.** Input → output. No side effects, no state, no imports from services.
- **A function that does A AND B must become two functions: A and B.**
- **Controllers/Views handle request/response mapping only.** No business logic inline.

### Responsibility Map

```
Entry Point      →  main.py / app.py
Request Layer    →  routes / controllers / views
Business Logic   →  services/
Data Access      →  repositories/
Data Models      →  models/
Validation       →  validators/
Pure Helpers     →  shared/utils/
Constants        →  shared/constants.py
Exceptions       →  shared/exceptions.py
Configuration    →  config/settings.py
```

### ✅ Correct
```python
# Each layer does exactly one thing

# repository.py — data access only
class UserRepository:
    def find_by_email(self, email: str) -> Optional[User]:
        return self._db.query(User).filter_by(email=email).first()

# service.py — business logic only
class AuthService:
    def login(self, email: str, password: str) -> str:
        user = self._repository.find_by_email(email)
        self._verify_password(user, password)
        return self._generate_token(user)
```

### ❌ Wrong
```python
class AuthService:
    def login(self, email, password):
        # direct DB query in service
        user = self._db.execute(f"SELECT * FROM users WHERE email='{email}'")
        # raw password hashing inline
        hashed = hashlib.sha256(password.encode()).hexdigest()
        # response formatting in service
        return {"status": 200, "token": "...", "message": "Login successful"}
```

---

## 10. Function Standards

**Principle:** All functions follow a single, consistent pattern. No function is too long or too vague.

### Rules

- **Maximum ~25–30 lines per function.** If a function exceeds this, it has more than one responsibility — split it.
- **Functions do exactly one thing.** Name it as a verb that describes that one thing precisely.
- **Function names must be descriptive and unambiguous:**
  - ✅ `fetch_user_by_id`, `validate_email_format`, `calculate_order_total`
  - ❌ `handle_stuff`, `process_data`, `do_action`, `run`
- **Parameters:** Maximum 3–4 positional parameters. If more are needed, use a dataclass or `TypedDict` as the parameter object.
- **Type hints on every function** — parameters and return type. Use `Optional[X]` instead of `X | None` for clarity (or consistently use union syntax `X | None` — pick one).
- **No side effects in pure utility functions.** A util that modifies external state is a service, not a util.
- **Early returns over nested conditions.** Fail fast and exit early — avoid deep nesting (`if` inside `if` inside `if`).
- **All functions that can fail must raise specific, named exceptions.** Never return `None` to signal failure — raise.
- **Consistent return types.** A function always returns the same type. Never conditionally returns a string sometimes and `None` other times without explicit typing.
- **No mutable default arguments.** Use `None` as default and assign inside the function body.

### ✅ Correct
```python
from typing import Optional
from shared.exceptions import UserNotFoundError
from features.auth.models import User

def fetch_user_by_email(email: str, repository: UserRepository) -> User:
    """Fetch a user record by email address.

    Args:
        email: The user's email address.
        repository: The data access layer for user records.

    Returns:
        A populated User instance.

    Raises:
        UserNotFoundError: If no user exists with the given email.
    """
    if not email:
        raise ValueError("Email must not be empty.")

    user = repository.find_by_email(email)

    if user is None:
        raise UserNotFoundError(f"No user found with email: {email}")

    return user
```

### ❌ Wrong
```python
def process_user(data, db=None, extra=[]):   # mutable default, vague name, no types
    if data:
        if data.get('email'):
            if db:
                user = db.execute("SELECT * FROM users WHERE email='" + data['email'] + "'")
                if user:
                    # format name
                    name = user['first'] + ' ' + user['last']
                    # send welcome email
                    import smtplib  # import inside function
                    smtp = smtplib.SMTP('localhost')
                    smtp.sendmail('noreply@app.com', data['email'], 'Welcome ' + name)
                    print("User processed")   # print in committed code
                    return user
    return None  # failure signalled by None return
```

---

## Enforcement Summary

| Rule Category | Key Signal of Violation |
|---|---|
| Modularization | File mixes concerns, exceeds ~200 lines, no `__init__.py` interface |
| OOP / SOLID | Class does multiple things, `new` inside method body, no DI |
| DRY | Same string/logic appears in 2+ places, magic numbers inline |
| No Dead Code | Unused import, commented-out block, `print()` statement |
| Consistency | Naming mismatch, mixed async styles, missing type hints |
| Import Discipline | Import inside function, wildcard import, unordered groups |
| State Management | Global mutable state, duplicated derived state |
| Coupling | Cross-layer direct import, circular import, no DI |
| Responsibility Overload | "and" in what a unit does, DB query inside service |
| Function Standards | Exceeds 30 lines, vague name, mutable default arg, `None` for failure |

---

*All rules apply from the first line of the first file to the last line of the last file.*
*Compliance is not optional. Quality is the baseline, not the goal.*
