import logging
import numbers
import os
import random
from pathlib import Path

import numpy as np
import yaml

from ekg.const import SEED

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Returns project's root folder (absolute path)"""
    return Path(__file__).parent.parent.parent


def to_absolute_path(path: str | os.PathLike) -> Path:
    """Converts relative paths to absolute paths to project root folder.

    If a segment is an absolute path, all previous segments are ignored. Returns
    absolute path.

    """
    return get_project_root() / Path(path)


def load_config(cfg_filename: str | Path = "config.yml") -> dict:
    """Loads YML config file from configs/ directory inside
    projects root folder. Fixes relative paths in 'paths' section of a config.
    Args:
        cfg_filename (str | Path, optional): Filename of a config.
            Defaults to Path("config.yml").

    Raises:
        ValueError: Not YAML file.
        FileNotFoundError: Config file is not found in configs/ dir.

    Returns:
        dict: Config dictionary.
    """
    if not isinstance(cfg_filename, (Path, str)):
        raise TypeError("Config filename must be either str or Path")

    cfg_filename = Path(cfg_filename)

    if cfg_filename.suffix.lower() not in (".yml", ".yaml"):
        raise ValueError("Config file must be YAML/YML format")

    cfg_path = to_absolute_path(Path("configs") / cfg_filename)

    if not cfg_path.is_file():
        raise FileNotFoundError(
            "Specified config path does not exist or is a directory"
        )

    with open(cfg_path, "r", encoding="UTF-8") as f:
        cfg = yaml.safe_load(f)
        logger.info("Loaded config from %s", cfg_path)

    cfg["paths"] = {
        k: to_absolute_path(path) for k, path in cfg["paths"].items()
    }
    logger.debug("Resolved config paths to absolute")
    return cfg


def setup(seed: int = None):
    if seed is None:
        seed = SEED

    if not isinstance(seed, numbers.Integral) or isinstance(seed, bool):
        raise TypeError(f"Seed must be integer value, got {type(seed)}")

    random.seed(seed)
    np.random.seed(seed)

    logging.basicConfig(
        format="[%(levelname)s] [%(name)s] %(asctime)s %(message)s",
        level=logging.INFO,
        # set to True so it overrides the basicConfig of jupyter notebooks
        force=True,
    )
