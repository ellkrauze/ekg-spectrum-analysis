import random
import re
from pathlib import Path

import numpy as np
import pytest
import yaml

from ekg.config import get_project_root, load_config
from ekg.config import setup as setup_ekg  # conflicts with pytest module
from ekg.config import to_absolute_path
from ekg.const import SEED

paths_test_data_relative = ["data/processed", "data/", "./data"]
paths_test_data_empty = ["", ".", "./"]


def test_get_project_root():
    assert (get_project_root() / "pyproject.toml").is_file()


@pytest.mark.parametrize("test_input", paths_test_data_relative)
def test_to_absolute_path_is_absolute(test_input):
    result = to_absolute_path(test_input)
    assert result.is_absolute()


def test_to_absolute_path_the_same(tmp_path):
    assert tmp_path == to_absolute_path(tmp_path)
    assert tmp_path == to_absolute_path(str(tmp_path))


@pytest.mark.parametrize("test_input", paths_test_data_relative)
def test_to_absolute_path_is_inside_root(test_input):
    result = to_absolute_path(test_input)
    assert result.is_relative_to(get_project_root())


@pytest.mark.parametrize("test_input", paths_test_data_relative)
def test_to_absolute_path_ends_with_folder(test_input):
    result = to_absolute_path(test_input)
    input_parts = Path(test_input).parts
    assert input_parts == result.parts[-len(input_parts) :]


@pytest.mark.parametrize("test_input", paths_test_data_empty)
def test_to_absolute_path_empty_returns_root(test_input):
    assert to_absolute_path(test_input) == get_project_root()


@pytest.mark.parametrize(
    "test_cfg_filename", ["test.ym", "noextension", "cfg.txt", "myyml"]
)
def test_load_config_not_yaml(test_cfg_filename):
    with pytest.raises(ValueError, match="Config file must be YAML/YML format"):
        load_config(test_cfg_filename)


TEST_CONFIG_CONTENT = {
    "paths": {
        "path1": "data/processed",
        "path2": "configs/",
        "another_path": "./",
        "empty": "",
    }
}


@pytest.fixture
def project_root(monkeypatch, tmp_path):
    monkeypatch.setattr("ekg.config.get_project_root", lambda: tmp_path)
    return tmp_path


@pytest.mark.parametrize(
    "test_cfg_filename", ["cfg.yml", "config.yaml", "config.YML"]
)
def test_load_config(test_cfg_filename, project_root):
    d = project_root / "configs"
    d.mkdir()
    cfg_file = d / test_cfg_filename
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(TEST_CONFIG_CONTENT, f, encoding="utf-8")

    expected = {
        "paths": {
            "path1": project_root / Path("data/processed"),
            "path2": project_root / Path("configs/"),
            "another_path": project_root,
            "empty": project_root,
        }
    }

    assert load_config(test_cfg_filename) == expected


@pytest.mark.parametrize(
    "test_cfg_filename", [1, {"cfg.yml"}, ("cfg.yml",), True]
)
def test_load_config_incorrect_type(test_cfg_filename):
    with pytest.raises(
        TypeError, match="Config filename must be either str or Path"
    ):
        load_config(test_cfg_filename)


@pytest.mark.parametrize("test_cfg_filename", ["cfg.yml", "config.yml"])
@pytest.mark.usefixtures("project_root")
def test_load_config_nonexistent_file(test_cfg_filename):
    with pytest.raises(
        FileNotFoundError,
        match="Specified config path does not exist or is a directory",
    ):
        load_config(test_cfg_filename)


@pytest.mark.parametrize("test_cfg_filename", ["cfg.yml", "config.yml"])
def test_load_config_is_directory(test_cfg_filename, project_root):
    d = project_root / "configs" / test_cfg_filename
    d.mkdir(parents=True)

    with pytest.raises(
        FileNotFoundError,
        match="Specified config path does not exist or is a directory",
    ):
        load_config(test_cfg_filename)


def gen_random_numbers():
    random_lst = [random.randint(0, 100) for _ in range(5)]
    random_lst += [np.random.randint(0, 100) for _ in range(5)]
    return random_lst


def test_setup_default():
    setup_ekg(SEED)
    expected = gen_random_numbers()
    setup_ekg()
    result = gen_random_numbers()
    assert result == expected


@pytest.mark.parametrize("test_input", [10, 100])
def test_setup_custom(test_input):
    setup_ekg(test_input)
    before = gen_random_numbers()

    setup_ekg(test_input)
    after = gen_random_numbers()

    assert before == after


@pytest.mark.parametrize("test_input", ["", True, [1, 2, 3], {}])
def test_setup_invalid_type(test_input):
    with pytest.raises(
        TypeError,
        match=re.escape(f"Seed must be integer value, got {type(test_input)}"),
    ):
        setup_ekg(test_input)


@pytest.mark.parametrize("test_input", [10, 100])
def test_setup_custom_different(test_input):
    setup_ekg(test_input)
    before = gen_random_numbers()

    setup_ekg(test_input + 1)
    after = gen_random_numbers()

    assert before != after
