"Plugin module for Borda Nauru"

# This file is part of agora-tally.
# Copyright (C) 2013-2016  Agora Voting SL <agora@agoravoting.com>

# agora-tally is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# agora-tally  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with agora-tally.  If not, see <http://www.gnu.org/licenses/>.

__revision__ = "$Id: Borda.py 715 2015-02-27 17:00:55Z edulix $"

from agora_tally.ballot_counter.STV import NonIterative
from agora_tally.ballot_counter.plugins import MethodPlugin

##################################################################

class BordaNauru(NonIterative, MethodPlugin):
  "Nauru Borda count"

  methodName = "BordaNauru"
  longMethodName = "Nauru Borda Count"
  status = 1

  htmlBody = """
<p>With the Borda count, candidates recieve points based on their
position on the ballots.  For example, if there are 4 candidates, then
a candidate receives 1 points for every first choice, 1/2 points for
every second choice, and 1/3 point for every third choice.  A candidate
receives no points if ranked last or not ranked at all.</p>
"""

  htmlHelp = (MethodPlugin.htmlBegin % (longMethodName, longMethodName)) +\
             htmlBody + MethodPlugin.htmlEnd

  def __init__(self, b):
    NonIterative.__init__(self, b)
    MethodPlugin.__init__(self)

    self.createGuiOptions([])

  def preCount(self):
    NonIterative.preCount(self)

    self.optionsMsg = ""
    self.prec = 0
    self.p = 10**self.prec

  def countBallots(self):
    "Count the votes using the Borda Count."

    # Add up the Borda counts
    for i in range(self.b.numWeightedBallots):
      weight, blt = self.b.getWeightedBallot(i)
      # Ranked candidates get their usual Borda score
      for j, c in enumerate(blt):
        self.count[c] += self.p * weight * (1.0 / (1+j))

    self.msg += "Borda count totals. "

    # Choose the winners
    desc = self.chooseWinners()
    self.msg += desc
