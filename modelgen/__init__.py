from modelgen.base import Base
from modelgen.helper import Helper
from utils import constants
from templates.alchemygen import alchemygen, metagen
from os import path, getcwd, walk
from jinja2 import Template
from pathlib import Path
from modelgen.parser import Parser

def create_model(datasource: str, alembic: bool=False) -> bool:
    h = Helper()
    filepath = path.join(constants.templates_folder, f"{datasource}.yaml")
    parser = Parser(filepath=filepath)
    src_template = Template(alchemygen)
    py_code = src_template.render(datasource=datasource,yaml_data=parser.data, cst=constants, bool=bool)
    Path(constants.models_folder).mkdir(parents=True, exist_ok=True)
    py_filepath = path.join(constants.models_folder, f'{datasource}.py')
    h.write_to_file(path=py_filepath, data=py_code)
    if alembic:
        create_alembic_meta(helper=h)
    return True

def create_alembic_meta(helper: Helper) -> bool:
    alembic_template = Template(metagen)
    _, _, filenames = next(walk(constants.models_folder))
    alembic_meta = alembic_template.render(filenames=filenames, cst=constants,
                                           splitext=path.splitext)
    Path(constants.alembic_meta_folder).mkdir(parents=True, exist_ok=True)
    alembic_meta_filepath = path.join(constants.alembic_meta_folder, '__init__.py')
    helper.write_to_file(path=alembic_meta_filepath, data=alembic_meta)
    return True