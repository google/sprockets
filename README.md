# Sprockets
*Last updated at 2016-11-30*

## 0. Disclaimer

* This is not an official Google product.
* This is tested only on Ubuntu though it would be running on any platforms which installed python and depending python packages.

## 1. Introduction
Sprockets is a framework for conformance testing based on state transitions.

To run conformance tests, Sprockets users should provide:

* a **test manifest** specifying the STL files, roles, and tests to run
* **STL files** describing a system defined with a set of protocols (or specifications)
* **External Python libraries** implementing external events and message encoders

State transitions are specified with STL (State Transition Language). See [STL.md](STL.md) for details of STL.

test_driver.py is the main program made of Python to run conformance tests specified by users with a test manifest, STL files, and python libraries.

## 2. test_driver.py
### 2.1. Environment Setup
To run test_dreiver.py, extra python packages below are necessary:

* google.protobuf
* ply
* networkx packages

If they are not installed already, follow commands below (tested only on Ubuntu):
```
$ pip install protobuf
$ pip install ply
$ pip install networkx
$ apt-get install libgraphviz-dev
$ pip install pygraphviz \
     --install-option="--include-path=/usr/include/graphviz" \
     --install-option="--library-path=/usr/lib/graphviz/"
```

### 2.2. Running
```
$ python test_driver.py [options] <test manifest>
```

### 2.3. Options
```
$ python test_driver.py -h
usage: test_driver.py [-h] [-a MANIFEST_ARGS] [-d] manifest

positional arguments:
  manifest              The manifest (*.test) file to run.

optional arguments:
  -h, --help            show this help message and exit
  -a MANIFEST_ARGS, --manifest-args MANIFEST_ARGS
                        A series of space separated key=value pairs. Each
                        instance of $key in the manifest file is replaced by
                        value verbatim. In particular, if you want to pass a
                        string, it must be explicitly quoted, e.g.:
                        ip="0.0.0.0"
  -d, --debug           Increase logging verbosity to debug level.
```

## 3. Test Manifest
The **test manifest** describes the tests to be run. The test manifest file typically has a .test extension. The manifest file is formatted as a python dictionary with three keys: ‘stl_files’, ‘roles’, and ‘test’.

### 3.1. Example manifest
```
example.test:

{
    'stl_files': ['example.stl'],

    'roles': [
        { 'role': 'example::rReceiver',
          'ipAddress': $ip,  # Must pass --manifest-args="ip='0.0.0.0'" to run.
          'transportId': 'receiver-0',
        },
    ],

    'test': ['example::rReceiver'],
}

$ python test_driver.py example/example.test --manifest-args=”ip=’0.0.0.0’”
```

### 3.2. stl_files
The ‘stl_files’ field must be a list of strings naming the STL files that include the transitions to be tested. The filenames here should be relative to the manifest .test file. In the example above, [example.test](example/example.test) and [example.stl](example/example.stl) are in the same directory.

### 3.3. roles
The ‘roles’ field must be list of dicts. Each dict element in the list describes one role. These are the roles described in the stl_files listed in the ‘stl_files’ field. In the above example, there [example.stl](example/example.stl) contains the following:
```
example.stl:

module example;
...
role rReceiver {
  string ipAddress;
  string transportId;
}
...
```

This gets transformed into
```
{
    'role': 'example::rReceiver',
    'ipAddress': $ip,  # Must pass --manifest-args="ip='0.0.0.0'" to run.
    'transportId': 'receiver-0',
}
```

The ‘role’ key maps to the ‘module:rRoleName’, which in this case is ‘example::rReceiver’.

The remaining key: value pairs map to the fields of the role as described in the STL file.

### 3.4. test
The ‘test’ field must be a list of strings naming the roles to be tested. Each entry in the test list must correspond to a ‘role’ value in the ‘roles’ list.

### 3.5. Substituting Parameters
Values can be substituted from the command line by passing a space separated list of key=value pairs to the --manifest-args option of test\_driver.py. The manifest .test file will then replace any occurence of $key with value. $key can be located anywhere in the manifest file (e.g. in the list of stl\_files, as a key or vparameter_example.test: test).
```
parameter_example.test:

{
    'stl_files': ['$STL_FILE'],

    'roles': [
        { 'role': '$TEST_ROLE',
          $FIELD: $VALUE,
          ‘my_number’: $my_number,
          ‘my_boolean’: $my_boolean,
          ‘str_no_quotes’: ‘$str_no_quotes’,
          ‘str_with_quotes’: $str_with_quotes,
        },
    ],

    'test': [‘$TEST_ROLE’],
}

$ python test_driver.py parameter_example.test --manifest-args=”\
    STL_FILE=example.stl \
    TEST_ROLE=example::rReceiver \
    FIELD=’new_field’ \
    VALUE=’new_value’ \
    my_number=3 \
    my_boolean=True \
    str_no_quotes=World \
    str_with_quotes=’bar’”
```

This is exactly equivalent to running with the following manifest:
```
parameter_example_with_substitues.test:
{
    'stl_files': ['example.stl'],

    'roles': [
        { 'role': 'example::rReceiver',
          ‘new_field’: ‘new_value’,
          ‘my_number’: 3,
          ‘my_boolean’: True,
          ‘str_no_quotes’: ‘Hello, World’,
          ‘str_with_quotes’: ‘bar’,
        },
    ],

    'test': [‘example::rReceiver’],
}
```
