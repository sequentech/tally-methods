#!/bin/bash

sudo apt-get install -y git virtualenvwrapper
source /etc/bash_completion.d/virtualenvwrapper
if [ ! -d $HOME/.virtualenvs/agora-tally ]
then
    mkvirtualenv agora-tally
fi
workon agora-tally
pip install -r testing_requirements.txt
