# Gra'Ma' Virtual Graph Machine

A Turing complete graph based RISC language.

### Data

A program's data consists of Concepts and Links, where each Concept is a node in the graph and each Link is a directed
edge from one Concept to another, via a third Concept.

### Instructions

* Create a Concept by naming it, e.g. ```my_concept``` creates a Concept named "my_concept".
* Create a link by providing a source and target path, e.g. ```my_concept/my_link_concept>my_other_concept``` creates a
Link "my_link_concept" from "my_concept" to "my_other_concept". Note that all three concepts must exist.
* Compare the identity of target concept from two paths and branch if same,
e.g. ```concept_a?concept_b/link_to_concept_a:jump_ofs``` will move the instruction pointer jump_ofs steps if
"concept_b" has a Link "link_to_concept_a" which targets "concept_a".

### Syntax

A Concept name is either a non-empty string which does not include special characters or a single-quoted string
consisting of zero or more characters excluding single quote, newline, carriage return and tab.
Both quoted and unquoted names may contain double-digit hex-encoded characters preceded by a backslash.

A path contains one or more Concept names separated by forward slash. When creating a link, the left-hand side path
must contain at least two segments, and as a special case, the right-hand side path may consist of a single unquoted
'+' to signify that a new concept should be created with an unspecified name, and should be targeted by the link.

* To create a Concept, simply name it. E.g. ```my\20concept``` or ```'my concept'```.
* To create a Link, provide link path and target path, separated by '>'. E.g. ```my_concept/my_link>my_other_concept```
or ```my_concept/my_link>my_other_concept/my_other_link```
* To compare and branch, provide two paths separated by '?', followed by ':' and an integer offset.
E.g. ```concept_a/link_a?concept_b/link_c/link_d:2```.

Statements must not span multiple lines, but may be separated by ';' to provide multiple statements on one line.
Line commens are allowed and begin on the first non-quoted '#'. Whitespace surrounding a statement is ignored.

### I/O

Special nodes are defined to provide input and output. The default nodes are stdin/read and stdout/write, which will
read or write the name of a concept, terminated by newline. If a concept is input which is unknown it will be created.

### Debugging

The debugger can be entered by linking ```stddbg/break``` to any concept, passing the -d command line argument,
sending SIGUSR1 to the process (the current instruction will complete before breaking), or using the "/debug" command in
the interactive interpreter.

The difference between interactive and debug mode is how statements entered on the command line affect the program's state:
* In interactive mode, statements will be retained in the program and the instruction pointer will be updated
* In debug mode, statements are executed then discarded and the instruction pointer remains unaffected

## Examples

Hello world:
```
Hello,\20World!
stdout/write>Hello,\20World!
```

Echo input (cat):
```
in; val
in/val>stdin/read
in/val?stdin/eof:3
stdout/write>in/val
in?in:-3
```

See more examples in "programs/".

## License

Distributed under the [MIT License](LICENSE.md).
