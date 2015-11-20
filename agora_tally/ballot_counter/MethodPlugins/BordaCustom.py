"Plugin module for Borda BordaCustom"

## Copyright (C) 2015 Felix Robles Elvira
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

__revision__ = "$Id: BordaCustom.py 715 2015-02-27 17:00:55Z edulix $"

from openstv.STV import NonIterative
from openstv.plugins import MethodPlugin

##################################################################

class BordaCustom(NonIterative, MethodPlugin):
  "Nauru Borda count"

  methodName = "BordaCustom"
  longMethodName = "Custom Borda Count"
  status = 1
  weightByPosition = None

  htmlBody = """
<p>With the Borda count, candidates recieve points based on their
position on the ballots. The BordaCustom class allows to define the 
points candidates receive for their position on the ballots.</p>
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
        self.count[c] += self.p * weight * self.weightByPosition[j]

    self.msg += "Borda count totals. "

    # Choose the winners
    desc = self.chooseWinners()
    self.msg += desc
