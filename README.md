
# pyvoog

An Model-Controller Python web framework, providing the following
capabilities:

* Routing (of incoming requests to controllers)
* Object-relational mapping based on the concept of models, built on top of
  SQLAlchemy
* Model validations
* Environment-based configuration
* Logging

## Development

Pyvoog uses Poetry for package management. Install Poetry globally as per the
[official instructions](https://python-poetry.org/docs/#installation).

Initialize and activate a Python virtual env.

```
$ virtualenv3 venv
$ . venv/bin/activate
```

To install the project's dependencies:

```
$ poetry install
```

To build the project:

```
$ poetry build
```

## License

Copyright (C) 2024 Edicy OÜ

This library is free software; you can redistribute it and/or modify it under
the terms of the [license](./LICENSE).

