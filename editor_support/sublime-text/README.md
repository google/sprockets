# Sublime Text Support

This folder contains various tools and configs for supporting STL and Sprockets
in Sublime Text.

## Syntax Highlighting

  1. Copy the `stl.YAML-tmLanguage` file to:
     `~/.config/sublime-text-2/Packages/User/stl.YAML-tmLanguage`
     This file defines how to highlight stl files in Sublime Text.

  2. Install the `PackageDev` package: https://github.com/SublimeText/PackageDev
     Follow the 'Getting Started' instructions in the README.

  3. In Sublime, open the `stl.YAML-tmLanguage` file.

  4. Open the command palette (Ctrl+Shift+P) and run:
     `PackageDev: Convert (YAML, JSON, PList) to...`
     This will convert the YAML syntax file into a Sublime Test property list,
     which can then be applied to your STL files.

  5. Open your STL file and open the command palette, selecting:
     `Set Syntax: State Transition Language`. This will apply the STL syntax
     highlighting to your file, if it is not already applied.
