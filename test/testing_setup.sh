#!/bin/bash

sudo apt-get install -y git virtualenvwrapper
source /etc/bash_completion.d/virtualenvwrapper
if [ ! -d $HOME/.virtualenvs/tally-methods ]
then
    mkvirtualenv tally-methods
fi
workon tally-methods
#pip install -r testing_requirements.txt
