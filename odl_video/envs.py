"""Functions reading and parsing environment variables"""

import os
from ast import literal_eval

from django.core.exceptions import ImproperlyConfigured


class EnvironmentVariableParseException(ImproperlyConfigured):
    """Environment variable was not parsed correctly"""


def get_string(name, default):
    """
    Get an environment variable as a string.

    Args:
        name (str): An environment variable name
        default (str): The default value to use if the environment variable doesn't exist.

    Returns:
        str:
            The environment variable value, or the default
    """
    return os.environ.get(name, default)


def get_bool(name, default):
    """
    Get an environment variable as a boolean.

    Args:
        name (str): An environment variable name
        default (bool): The default value to use if the environment variable doesn't exist.

    Returns:
        bool:
            The environment variable value parsed as a bool
    """
    value = os.environ.get(name)
    if value is None:
        return default

    parsed_value = value.lower()
    if parsed_value == "true":
        return True
    elif parsed_value == "false":
        return False

    raise EnvironmentVariableParseException(
        "Expected value in {name}={value} to be a boolean".format(
            name=name,
            value=value,
        )
    )


def get_int(name, default):
    """
    Get an environment variable as an int.

    Args:
        name (str): An environment variable name
        default (int): The default value to use if the environment variable doesn't exist.

    Returns:
        int:
            The environment variable value parsed as an int
    """
    value = os.environ.get(name)
    if value is None:
        return default

    try:
        parsed_value = int(value)
    except ValueError as ex:
        raise EnvironmentVariableParseException(
            "Expected value in {name}={value} to be an int".format(
                name=name,
                value=value,
            )
        ) from ex

    return parsed_value


def get_list_of_str(name, default):
    """
    Get an environment variable as a list of strings.

    Args:
        name (str): An environment variable name
        default (list): The default value to use if the environment variable doesn't exist.

    Returns:
        list of str:
            The environment variable value parsed as a list of strings
    """
    value = os.environ.get(name)
    if value is None:
        return default

    parse_exception = EnvironmentVariableParseException(
        "Expected value in {name}={value} to be a list of str".format(
            name=name,
            value=value,
        )
    )

    try:
        parsed_value = literal_eval(value)
    except (ValueError, SyntaxError) as ex:
        raise parse_exception from ex

    if not isinstance(parsed_value, list):
        raise parse_exception

    for item in parsed_value:
        if not isinstance(item, str):
            raise parse_exception

    return parsed_value


def get_any(name, default):
    """
    Get an environment variable as a bool, int, or a string.

    Args:
        name (str): An environment variable name
        default (any): The default value to use if the environment variable doesn't exist.

    Returns:
        any:
            The environment variable value parsed as a bool, int, or a string
    """
    try:
        return get_bool(name, default)
    except EnvironmentVariableParseException:
        try:
            return get_int(name, default)
        except EnvironmentVariableParseException:
            return get_string(name, default)


def get_key(name, default):
    """
    Get an environment variable as a string representing a private or public key.
    The difference is that keys are automatically escaped and they need to be unescaped and
    encoded into bytestrings.

     Args:
        name (str): An environment variable name
        default (str): The default value to use if the environment variable doesn't exist.

    Returns:
        bytes: The environment variable value, or the default as bytestring
    """
    value = get_string(name, default)
    if not isinstance(value, str):
        return value
    return value.encode().decode("unicode_escape").encode()


def parse_env(env_file):
    """
    Parse the env file and set the values in the runtime environment.
    Simplifies deployment by ensuring env values are present without
    duplicating across multiple locations and not requiring explicit
    sourcing.

    Args:
      env_file (str): path to a file consisting of key=value pairs

    Returns:
      None: No return value

    """
    try:
        with open(env_file, encoding="utf-8") as envsettings:
            for line in envsettings:
                try:
                    k, v = line.rstrip("\n").lstrip("export ").split("=", maxsplit=1)
                    os.environ.setdefault(k, v)
                except ValueError:
                    continue
    except FileNotFoundError:
        pass
