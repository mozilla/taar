# Randomized tail selection of addons

The `TAAR_EXPERIMENT_PROB` sets a probability that a user is in an experiment
to get randomized recommendations.

Randomized recommendations does not mean that recommendations are
fully randomized.  Weights for each recommendation are normalized to
so that the sum of weights equals 1.0.

Using `numpy.random.choice` - we then select a non-uniform random
sample from the list of suggestions without replacement.  Weights are
used to define a vector of probabilities.


By default - TAAR_EXPERIMENT_PROB is set to 0.0 which in effect
disables the randomization feature.
