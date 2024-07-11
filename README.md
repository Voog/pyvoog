
# pyvoog

An Model-Controller Python web framework, providing the following
capabilities:

* Routing (of incoming requests to controllers)
* Object-relational mapping based on the concept of models, built on top of
  SQLAlchemy
* Model validations
* Environment-based configuration
* Logging

## Building

Initialize and activate a Python virtual env.

```
$ virtualenv3 venv
$ . venv/bin/activate
```

Install `build`.

```
$ pip install build
```

Build the project.

```
$ python -m build
```

## License

Copyright (C) 2024 Edicy OÜ

This library is free software; you can redistribute it and/or modify it under
the terms of the [license](./LICENSE).

