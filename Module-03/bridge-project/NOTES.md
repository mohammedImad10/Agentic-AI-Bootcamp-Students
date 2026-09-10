# Notes

## a. Where did the budget force a real trade-off?

The budget had to be spent where the legal identity was genuinely ambiguous, not where the name was simply famous. I chose not to spend the remaining lookup on C & V Works ApS because it was the lowest-value supplier and the residual risk was deliberately accepted in exchange for using the same nine-lookup budget on the more important ambiguities: Siemens AG, Almarai Company, and Zorblax Trading FZE.

## b. What sanctions threshold did I set, and why that number?

I set the sanctions rejection threshold at 0.90. The critical comparison is Al Wasel and Babel General Trading LLC, which scored 1.00 on the OFAC list, versus Almarai Company, which scored 0.81 because it shared generic words like 'Company' with a genuinely alarming sanctions entry. A lower threshold would have blocked a real business; a higher threshold would have let a true sanctioned entity through. The 0.90 threshold is the safe practical line for this case.

## c. Where did the agent nearly get it wrong?

The near-miss was Siemens AG. A naive agent would have approved the first GLEIF candidate it saw, such as Siemens Energy AG, because the register returns several similarly named subsidiaries. The actual problem is that none of the returned entities is named exactly 'Siemens AG'; so I treated zero exact matches as CONDITIONS rather than APPROVE. That is the most common real supplier-onboarding failure and exactly the trap the brief warns about.

The verdicts are stable because the logic is deterministic and based on actual registry evidence rather than a free-form model guess.

