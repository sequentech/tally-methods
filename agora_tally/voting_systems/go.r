###############################################################################
#
# Calculate strengths from pairwise comparisons using the bradley terry model
#
# see
#
# http://www.jstatsoft.org/v48/i09/paper
# http://www.r-bloggers.com/mlb-rankings-using-the-bradley-terry-model/
# https://github.com/ramhiser/baseball-rankings/blob/master/lib/helpers.R
#
###############################################################################


# helper functions
#
# to go from abilities to probabilities:
# See equation (1) in paper:
#
# "The model can alternatively be expressed in the logit-linear form
# logit[pr(i beats j)] = Lambdai - Lambdaj"   (1)
#

#' Inverse logit of a probability
#'
#' @param p probability
#' @return the inverse logit of \code{p}
inv_logit <- function(p) {
  exp(p) / (1 + exp(p))
}

#' Given two teams abilities estimated via a Bradley-Terry model, this function
#' calculates the probability that team 1 will beat team 2.
#'
#' @param ability_1 team 1's ability under a Bradley-Terry model
#' @param ability_2 team 2's ability under a Bradley-Terry model
#' @return probability that team 1 beats team 2
prob_BT <- function(ability_1, ability_2) {
  inv_logit(ability_1 - ability_2)
}

# read pairwise data, format is:
# team 1, team 2, team1 wins, team 2 wins
args <- commandArgs(trailingOnly = TRUE)
mydata = read.table(args)

print(mydata)
library("BradleyTerry2")

# this is necessary to create factors with the same levels
lv <- union(unique(mydata$V2), unique(mydata$V1))
mydata$V1 = factor(mydata$V1, levels = lv)
mydata$V2 = factor(mydata$V2, levels = lv)

# create the model
myModel <- BTm(cbind(V3, V4), V1, V2, ~ option,  id = "option", data = mydata)

# extract abilities
abilities <- BTabilities(myModel)
print(abilities)

# use the below if we need to extract probabilities for each comparison

# get probabilities (see helper functions above)
# probs <- outer(abilities, abilities, prob_BT)
# diag(probs) <- 0
# print(probs)