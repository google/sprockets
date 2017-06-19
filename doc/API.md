# API to define builtin events and functions
*Last updated at 2017-02-27*

## 1. Python API Documentation
Documentation for various Sprockets Python modules is located at ```$PROJECT_ROOT/doc/html/index.html```. Up-to-date documentation can be viewed [here](https://htmlpreview.github.io/?https://github.com/google/sprockets/blob/master/doc/html/index.html).

User-defined abstract classes (events, qualifiers, encodings, etc) are defined in the ```sprockets.stl.lib``` module.

For instructions on how to write an STL file, see [STL.md](STL.md).

## 2. Documentation Generation
Python documentation can be automatically generated from the project root by running:

```
cd $SPROCKETS_ROOT
epydoc --exclude='.*pb2|.*proto.*' -o doc/html .
```
