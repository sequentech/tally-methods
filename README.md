agora-tally
===========

agora-tally provides functions for tallying election data using OpenSTV as the underlying library when necessary


## Entry functions

The entry point for tally processing is either

* do_dirtally(dir_path)

Tallies election data found in the given directory

* do_tartally(tally_path)

Tallies election data found in the given tar.gz file.

## Input format

Both the tar and directory functions expect the same file structure for election data:

<root>
|
|- result_json (file desribing the election questions and types)
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

### result_json format

TODO

Please refer to the test/fixtures directory for samples of election data.

### plaintexts_json format

TODO

Please refer to the test/fixtures directory for samples of election data.

## Voting methods

The following methods are supported

* ONE_CHOICE

Classic plurality method with one winner.

* MEEK-STV

Preferential, single transferable voting for selecting a list of candidates, uses Meek's method.

* APPROVAL (FIXME what happens with ties)

Refers to both approval (one winner) and plurality-at-large (list of winners) methods where ballots reflect
approval of candidates with no order specified.

## Testing

In order to run tests you have to set up a virtual environment in which to install the OpenSTV dependency. The script

test/testing_setup.sh

is provided to do this. When testing you have to activate the environment with

workon agora-tally

Then run the tests with

 python -m unittest discover