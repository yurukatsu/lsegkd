import datetime
from typing import Literal

from loguru import logger


def parse_datetime(
    datetime_str: str, *, drop_microseconds: Literal[True] = True
) -> datetime.datetime:
    """
    Parse a datetime string into a datetime object using multiple patterns.

    Args:
        datetime_str (str): The datetime string to parse.
        drop_microseconds (Literal[True], optional): Whether to drop microseconds from the string.
            Defaults to True.

    Returns:
        datetime.datetime: The parsed datetime object.
    """
    if drop_microseconds:
        datetime_str = datetime_str.split(".")[0] + "Z"

    patterns = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT %H:%M:%SZ",
        "%Y-%m-%dT %H:%M:%S",
        "%Y-%m-%d T%H:%M:%SZ",
        "%Y-%m-%d T%H:%M:%S",
        "%Y-%m-%d T %H:%M:%SZ",
        "%Y-%m-%d T %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H-%M-%SZ",
        "%Y-%m-%dT%H-%M-%S",
        "%Y-%m-%dT %H-%M-%SZ",
        "%Y-%m-%dT %H-%M-%S",
        "%Y-%m-%d T%H-%M-%SZ",
        "%Y-%m-%d T%H-%M-%S",
        "%Y-%m-%d T %H-%M-%SZ",
        "%Y-%m-%d T %H-%M-%S",
        "%Y-%m-%d %H-%M-%S",
        "%Y%m%dT%H%M%SZ",
        "%Y-%m-%d-%H-%M-%S",
        "%Y%m%d %H%M%SZ",
        "%Y-%m-%d",
        "%Y%m%d",
    ]

    for pattern in patterns:
        try:
            return datetime.datetime.strptime(datetime_str, pattern)
        except Exception as e:
            logger.debug(f"Pattern {pattern} did not match: {e}")
    raise ValueError(f"Unrecognized datetime format: {datetime_str}")
