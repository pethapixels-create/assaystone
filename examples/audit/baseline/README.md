# Demo project

A tiny pricing library used by the Assaystone demo. Two tests fail before the
agent's patch: discounts must round half-up to the nearest cent, and the
current implementation truncates.
