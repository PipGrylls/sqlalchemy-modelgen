from os import path, getcwd, walk
from pathlib import Path
from shutil import copyfile, copytree
from typing import Optional
from jinja2 import Template

from .helper import Helper
from . import (__file__, constants, Validate, Parser, alchemygen, flaskgen, metagen)


class ModelGenerator(Helper):

    def __init__(self, init: Optional[str] = False, createmodel: bool = False,
                 file: str = None, alembic: bool = False, target: str = False,
                 **kwargs):
        """
        This class is initialized by taking in the argument values 
        passed from the cli. 

        Args: 
            init (Optional[str] or False): init is set to true if 
                --init is called from the cli and a folder name is
                passed. The folder name has to be new, if an existing
                folder name is passed, an exception will be raised
                asking to pass a new folder name/path. 
                If init is not called from cli, it is set to False 
                by default.

            createmodel (bool): createmodel is set to true if 
                --createmodel is called from the command line.
                --createmodel also needs another argument
                -f or --file which points to the path of the 
                schema yaml file. This file will be used to create
                sqlalchemy model code in python

            file (str): filepath of the yaml schema template file.
            
            alembic (bool): if set, alembic support will be set
                to true. A folder named metadata will be created
                with an __init__.py. This py file will have the
                sqlalchemy metadata imported from the file 
                generated by the createmodel command.
        """
        Helper.__init__(self)
        self.create_structure(init=init)
        self.create_models(createmodel=createmodel, file=file, alembic=alembic, target=target)

    def _create_template_folder(self, **kwargs) -> bool:
        """
        Create a folder called `templates`. This folder contains an
        example schema template file required to get started.

        Returns bool, True if creation is successful, False otherwise. 
        """
        try:
            init = kwargs.get('init')
            templates_src_path = path.join('/', *(__file__.split('/')[:-1]), 'templates')
            templates_dst_path = path.join(init, 'templates')
            if path.exists(templates_dst_path):
                raise FileExistsError
            self.logger.info(f'Creating templates folder at {templates_dst_path}')
            Path(templates_dst_path).mkdir(parents=True, exist_ok=False)
            self.logger.debug('Templates folder creation successful')
            self.logger.info(f'Creating an example yaml schema file at {templates_dst_path}/example.yaml')
            copyfile((path.join(templates_src_path, 'example.yaml')),
                     path.join(templates_dst_path, 'example.yaml'))
            return True
        except FileExistsError as e:
            self.logger.exception('Error occurred while creating templates folder')
            self.logger.exception(e)
            raise FileExistsError("Folder exists. Please specify a new folder name") from FileExistsError

    def _create_alembic_folder(self, **kwargs):
        """
        This function is responsible for creating alembic's 
        folder structure. The folder created is named `alembic`.
        This folder contains files __init__.py, evn.py, README,
        script.py.mako and a folder named `versions`. This folder
        stores version files for every table level change made.

        Returns bool, True if folder creation is successful,
        False otherwise.
        """
        try:
            init = kwargs.get('init')
            if path.isabs(init):
                dst_path = path.join(init)
            else:
                dst_path = path.join(getcwd(), init)
            if path.exists(dst_path):
                raise FileExistsError
            alembic_path = path.join('/', *(__file__.split('/')[:-1]), 'alembic_migrate')
            self.logger.info(f'Creating alembic folder at {dst_path}')
            ini_src_path = path.join('/', *(__file__.split('/')[:-1]), 'alembic.ini')
            copytree(alembic_path, path.join(dst_path, 'alembic_migrate'))
            # Path(path.join(self.dst_path, 'alembic','versions')).mkdir(parents=True, exist_ok=False)
            copyfile(ini_src_path, path.join(dst_path, 'alembic.ini'))
            return True
        except FileExistsError as e:
            self.logger.exception('Error occurred while creating alembic folder')
            self.logger.exception(e)
            raise FileExistsError("Folder exists. Please specify a new folder name") from FileExistsError

    def _create_checkpoint_file(self, **kwargs) -> bool:
        """
        Create a checkpoint file in the folder name/path
        passed while initializing  modelgen. The file created
        is named `.modelgen`. This file let's the program know
        that modelgen has been initialized in the directory

        Returns bool, True if successful, False otherwise.
        """
        init = kwargs.get('init')
        self.write_to_file(path=path.join(init, '.modelgen'), data='')
        return True

    def _find_checkpoint_file(self) -> bool:
        """
        Check if the checkpoint file `.modelgen` exists in
        the directory or not. This function is run before 
        creating the sqlalchemy python code.

        Returns bool, True if file exists, False if file
        doesn't exist.
        """
        chkpnt_filepath = path.join(getcwd(), '.modelgen')
        if not path.exists(chkpnt_filepath):
            err_str = 'Either modelgen is not initialized, or you are in the wrong folder\n'
            err_str += 'Please initialize modelgen (modelgen --source yaml --init ./YOUR_FOLDER_NAME)'
            err_str += ' or execute commands from /path/YOUR_FOLDER_NAME'
            raise FileNotFoundError(err_str)
        else:
            return True

    def _create_model(self, datasource: str, alembic: bool = False,
                      filepath: str = None, target: str = None) -> bool:
        """
        Create sqlalchemy code, based on the schema
        defined in the yaml schema template file. The code files
        are created in a folder called `models` and the files
        are created by the datasource name. Example: if the datasource 
        name is inventory, the model file will be 
        `models/inventory.py`.

        Args:
            datasource (str): name of the datasource.
                This is defined by the name of the
                schema template yaml file. 
                for example, if the schema file is named 
                inventory.yaml, the datasource name will be 
                inventory

            alembic (bool, default: False): If set to True,
                python code to support alembic migrations 
                will also be created.

            filepath (str, default: None): filepath of the
                schema template yaml file. If nothing is passed,
                a path will be constructed using current directory
                and the datasource name. This consturcted path
                will be current_working_dir/templates/datasource.yaml

        Returns:
            (bool): True, if sqlalchemy model code generation is successful
                    False, if sqlalchemy model code generation fails
        """
        if target is not None:
            if target == 'flaskgen':
                template = flaskgen
            else:
                raise ValueError(target)
        else:
            template = alchemygen
        if not filepath:
            filepath = path.join(constants.templates_folder, f"{datasource}.yaml")
        Validate(filepath=filepath).validate()
        parser = Parser(filepath=filepath)
        src_template = Template(template)
        py_code = src_template.render(datasource=datasource, yaml_data=parser.data, cst=constants, bool=bool)
        Path(constants.models_folder).mkdir(parents=True, exist_ok=True)
        py_filepath = path.join(constants.models_folder, f'{datasource}.py')
        self.write_to_file(path=py_filepath, data=py_code)
        if alembic:
            self._create_alembic_meta()
        return True

    def _create_alembic_meta(self) -> bool:
        """
        Creates code required to support alembic migrations.
        The code is created in a folder `metadata`. A file
        named __init__.py is created in the `metadata` folder
        which imports the sqlalchemy metadata from all the models
        sitting in the `models` folder.

        Returns bool, True if code creation is successful,
        False if code creation fails.
        """
        alembic_template = Template(metagen)
        _, _, filenames = next(walk(constants.models_folder))
        alembic_meta = alembic_template.render(filenames=filenames, cst=constants,
                                               splitext=path.splitext)
        Path(constants.alembic_meta_folder).mkdir(parents=True, exist_ok=True)
        alembic_meta_filepath = path.join(constants.alembic_meta_folder, '__init__.py')
        self.write_to_file(path=alembic_meta_filepath, data=alembic_meta)
        return True

    def create_structure(self, init: bool = False) -> bool:
        if bool(init):
            self._create_alembic_folder(init=init)
            self._create_template_folder(init=init)
            self._create_checkpoint_file(init=init)
            return True
        return None

    def create_models(self,
                      createmodel: bool = False,
                      file: str = None,
                      alembic: bool = False,
                      target: str = None) -> bool:
        if bool(createmodel):
            self._find_checkpoint_file()
        if bool(file):
            if file.endswith('.yaml'):
                datasource = file.split('.yaml')[0].split('/')[-1]
            elif file.endswith('yml'):
                datasource = file.split('.yml')[0].split('/')[-1]
            else:
                raise NameError('Please specify a .yaml or .yml file')
            self.logger.info(f"Creating models at {file}")
            self._create_model(datasource=datasource, alembic=alembic, target=target)
            return True
        return None
