import logging
import os
import random
from pathlib import Path

import numpy as np
import yaml

from ekg.const import SEED

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    return Path(__file__).parent.parent.parent


def to_absolute_path(path: str | os.PathLike) -> Path:
    return get_project_root() / Path(path)


def load_config(cfg_filename: str = "config.yml") -> dict:
    if isinstance(cfg_filename, Path):
        cfg_filename = str(cfg_filename)

    if not cfg_filename.lower().endswith(("yml", "yaml")):
        raise ValueError("Config file must be YAML/YML format")

    cfg_path = os.path.join(get_project_root(), "configs", cfg_filename)

    if not os.path.exists(cfg_path):
        raise FileNotFoundError(
            "Specified config path does not exist, make sure to store it\
                in configs/ directory inside the project's root folder"
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

    random.seed(seed)
    np.random.seed(seed)

    logging.basicConfig(
        format="[%(levelname)s] [%(name)s] %(asctime)s %(message)s",
        level=logging.INFO,
        # set to True so it overrides the basicConfig of jupyter notebooks
        force=True,
    )
