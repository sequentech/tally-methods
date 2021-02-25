# agora-tally [![tests_badge]][tests_link]

agora-tally provides functions for tallying election data using OpenSTV as the underlying library when necessary

[tests_badge]: https://github.com/agoravoting/agora-tally/workflows/Test%20python/badge.svg
[tests_link]: https://github.com/agoravoting/agora-tally/actions?query=workflow%3A%22Test+python%22

### Entry functions

The entry point for tally processing is either

* do_dirtally(dir_path)

Tallies election data found in the given directory

* do_tartally(tally_path)

Tallies election data found in the given tar.gz file.

### Input format

Both the tar and directory functions expect the same file structure for election data:

```
<root>
|
|- questions_json (file describing the election questions)
|
|--- 0-xxxxx (directory with data for the 0th question)
|    |
|    |
|    --  plaintexts_json (file containing votes, one per line)
...
|
|--- n-xxxxx (directory with data for the nth question)
     |
     |
     --  plaintexts_json (file containing votes, one per line)
```

#### result_json format

TODO

Please refer to the test/fixtures directory for samples of election data.

#### plaintexts_json format

TODO

Please refer to the test/fixtures directory for samples of election data.

### Voting methods

The following methods are currently supported:
* plurality-at-large

Refers to both approval (one winner) and plurality-at-large (list of winners) methods where ballots reflect
approval of candidates with no order specified.

### Testing

In order to run tests you have to set up a virtual environment in which to install the OpenSTV dependency. The script

test/testing_setup.sh

is provided to do this. When testing you have to activate the environment with

```workon agora-tally```

Then run the tests with

 ```python -m unittest discover```

# License

Copyright (C) 2015 Agora Voting SL and/or its subsidiary(-ies).
Contact: legal@agoravoting.com

This file is part of the agora-core-view module of the Agora Voting project.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

Commercial License Usage
Licensees holding valid commercial Agora Voting project licenses may use this
file in accordance with the commercial license agreement provided with the
Software or, alternatively, in accordance with the terms contained in
a written agreement between you and Agora Voting SL. For licensing terms and
conditions and further information contact us at legal@agoravoting.com .

GNU Affero General Public License Usage
Alternatively, this file may be used under the terms of the GNU Affero General
Public License version 3 as published by the Free Software Foundation and
appearing in the file LICENSE.txt included in the packaging of this file, or
alternatively found in <http://www.gnu.org/licenses/>.

External libraries
This program distributes libraries from external sources. If you follow the
compilation process you'll download these libraries and their respective
licenses, which are compatible with our licensing.
